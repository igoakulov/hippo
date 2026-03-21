import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

INCLUDE_CONTENT_TYPES = {
    "text",
    "code",
    "execution_output",
    "tether_quote",
    "sonic_webpage",
    "system_error",
    "multimodal_text",
}

EXCLUDE_CONTENT_TYPES = {
    "user_editable_context",
    "thoughts",
    "reasoning_recap",
    "tether_browsing_display",
    "app_pairing_content",
}

EXCLUDE_ROLES = {"system", "tool"}


@dataclass
class MessageNode:
    id: str
    role: str
    content: str
    timestamp: str
    content_type: str
    language: str = ""
    branch_depth: int = 0


@dataclass
class Conversation:
    id: str
    title: str
    create_time: float
    messages: list[MessageNode] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)


@dataclass
class IngestLog:
    conversation_id: str
    output_file: str
    last_message_id: str
    source_hash: str
    ingested_at: str
    filters: dict[str, Any] | None = None


def load_conversations(path: Path) -> list[dict]:
    path = path.expanduser().resolve()

    if path.suffix.lower() in (".zip", ".rar"):
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("conversations.json"):
                    with zf.open(name) as f:
                        return json.loads(f.read().decode("utf-8"))
        raise ValueError(f"No conversations.json found in {path}")
    else:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def filter_conversations(
    conversations: list[dict],
    from_time: float | None,
    till_time: float | None,
    titles: list[str] | None,
) -> list[dict]:
    titles_lower = [t.lower() for t in titles] if titles else None

    result = []
    for conv in conversations:
        create_time = conv.get("create_time", 0)

        if from_time is not None and create_time < from_time:
            continue
        if till_time is not None and create_time > till_time:
            continue

        if titles_lower:
            title = conv.get("title", "").lower()
            if not any(t in title for t in titles_lower):
                continue

        result.append(conv)

    return result


def should_include_message(msg: dict) -> bool:
    if msg is None:
        return False

    author = msg.get("author", {})
    role = author.get("role", "")

    if role in EXCLUDE_ROLES:
        return False

    if role not in ("user", "assistant"):
        return False

    content = msg.get("content", {})
    content_type = content.get("content_type", "")

    if content_type in EXCLUDE_CONTENT_TYPES:
        return False

    if content_type not in INCLUDE_CONTENT_TYPES:
        return False

    metadata = msg.get("metadata", {})
    if metadata.get("is_visually_hidden_from_conversation"):
        return False

    text, _, _ = extract_content(msg)
    if not text or not text.strip():
        return False

    if text.strip() == "{}":
        return False

    return True


def extract_content(msg: dict) -> tuple[str, str, str]:
    content = msg.get("content", {})
    content_type = content.get("content_type", "")
    language = content.get("language", "")

    if content_type == "code":
        text = content.get("text", "")
    else:
        parts = content.get("parts", [])
        text = "\n\n".join(str(p) for p in parts) if parts else ""

    return text, content_type, language


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)


def format_timestamp(create_time: float) -> str:
    dt = datetime.fromtimestamp(create_time)
    return dt.isoformat()


def slugify_title(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    slug = slug.strip("-")
    return slug


def parse_conversation(conv: dict) -> Conversation:
    conv_id = conv.get("conversation_id") or conv.get("id", "")
    title = conv.get("title", "Untitled")
    create_time = conv.get("create_time", 0)

    mapping = conv.get("mapping", {})

    root = None
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            root = node_id
            break

    messages: list[MessageNode] = []
    urls: list[str] = []

    if root:
        _traverse_messages(
            mapping, root, None, messages, urls, branch_depth=0, first_branch=True
        )

    return Conversation(
        id=conv_id,
        title=title,
        create_time=create_time,
        messages=messages,
        urls=urls,
    )


def _traverse_messages(
    mapping: dict,
    node_id: str,
    parent_id: str | None,
    messages: list[MessageNode],
    urls: list[str],
    branch_depth: int,
    first_branch: bool,
) -> str | None:
    node = mapping.get(node_id)
    if not node:
        return None

    if node.get("parent") != parent_id:
        return None

    msg = node.get("message")

    last_msg_id = node_id

    if should_include_message(msg):
        content, content_type, language = extract_content(msg)
        create_time = msg.get("create_time") or 0

        if content:
            message_urls = extract_urls(content)
            urls.extend(message_urls)

            messages.append(
                MessageNode(
                    id=node_id,
                    role=msg["author"]["role"],
                    content=content,
                    timestamp=format_timestamp(create_time),
                    content_type=content_type,
                    language=language,
                    branch_depth=branch_depth,
                )
            )

    children = node.get("children") or []

    if children:
        first = True
        for child_id in children:
            child_branch_depth = branch_depth
            if first:
                first = False
            else:
                child_branch_depth = branch_depth + 1

            child_last = _traverse_messages(
                mapping, child_id, node_id, messages, urls, child_branch_depth, first
            )
            if child_last:
                last_msg_id = child_last

    return last_msg_id


def message_to_markdown(msg: MessageNode) -> str:
    lines = []

    role_prefix = "USER" if msg.role == "user" else "ASSISTANT"

    if msg.branch_depth > 0:
        prefix = "> " * msg.branch_depth
        lines.append(f"{prefix}{role_prefix} · {msg.timestamp}")
        for line in msg.content.split("\n"):
            lines.append(f"{prefix}{line}")
    else:
        lines.append(f"{role_prefix} · {msg.timestamp}")
        lines.append("")
        lines.append(msg.content)

    if msg.content_type == "code":
        lang = msg.language if msg.language else ""
        content_lines = msg.content.split("\n")
        if msg.branch_depth > 0:
            prefix = "> " * msg.branch_depth
            lines.clear()
            lines.append(f"{prefix}{role_prefix} · {msg.timestamp}")
            lines.append(f"{prefix}")
            lines.append(f"{prefix}```{lang}")
            for line in content_lines:
                lines.append(f"{prefix}{line}")
            lines.append(f"{prefix}```")
        else:
            lines.append("")
            lines.append(f"```{lang}")
            lines.extend(content_lines)
            lines.append("```")

    return "\n".join(lines)


def conversation_to_markdown(
    conv: Conversation,
    source_path: str,
    word_count: int,
    created_at: str,
    updated_at: str,
    last_message_id: str = "",
) -> str:
    lines = ["---"]
    lines.append(f"id: {conv.id}")
    lines.append(f"title: {conv.title}")
    lines.append(f"created_at: {created_at}")
    lines.append(f"updated_at: {updated_at}")
    lines.append(
        f"original_conversation_created_at: {format_timestamp(conv.create_time)}"
    )
    lines.append(f"word_count: {word_count}")
    lines.append("sources:")
    lines.append(f"  - {source_path}")
    for url in conv.urls:
        lines.append(f"  - {url}")
    if last_message_id:
        lines.append(f"last_message_id: {last_message_id}")
    lines.append("---")
    lines.append("")

    for msg in conv.messages:
        if msg.branch_depth > 0:
            continue
        lines.append(message_to_markdown(msg))
        lines.append("")
        lines.append("---")
        lines.append("")

    for msg in conv.messages:
        if msg.branch_depth > 0:
            lines.append(message_to_markdown(msg))
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines).strip()


def compute_word_count(conv: Conversation) -> int:
    count = 0
    for msg in conv.messages:
        count += len(msg.content.split())
    return count


def get_last_message_id(conv: Conversation) -> str:
    if conv.messages:
        return conv.messages[-1].id
    return ""


def get_output_filename(conv: Conversation) -> str:
    slug = slugify_title(conv.title)
    dt = datetime.fromtimestamp(conv.create_time).strftime("%Y-%m-%dT%H-%M-%S")
    return f"{slug}_{dt}.md"


def parse_conversation_expand(
    conv_data: dict, last_message_id: str | None
) -> Conversation:
    conv = parse_conversation(conv_data)

    if last_message_id:
        seen_last = False
        filtered_messages = []
        for msg in conv.messages:
            if seen_last:
                filtered_messages.append(msg)
            elif msg.id == last_message_id:
                seen_last = True
        conv.messages = filtered_messages

    return conv


def get_existing_last_message_id(file_path: Path) -> str | None:
    if not file_path.exists():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
        fm_pattern = re.compile(r"^last_message_id:\s*(.+)$", re.MULTILINE)
        match = fm_pattern.search(content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None


def get_existing_file_for_conversation(
    chats_dir: Path, conversation_id: str
) -> Path | None:
    for md_file in chats_dir.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            id_pattern = re.compile(r"^id:\s*(.+)$", re.MULTILINE)
            match = id_pattern.search(content)
            if match and match.group(1).strip() == conversation_id:
                return md_file
        except Exception:
            continue
    return None


def get_stem_from_filename(filename: str) -> str:
    return filename.rsplit(".", 1)[0]


def get_log_entries(logs_dir: Path) -> list[dict]:
    entries = {}
    if not logs_dir.exists():
        return []
    for log_file in sorted(logs_dir.glob("ingest_*.json")):
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            for entry in data:
                conv_id = entry.get("conversation_id")
                if conv_id:
                    entries[conv_id] = entry
        except Exception:
            continue
    return list(entries.values())
