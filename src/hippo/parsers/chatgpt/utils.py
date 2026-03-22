import json
import re
from datetime import datetime
from pathlib import Path

from hippo.parsers.chatgpt.models import Conversation


def slugify_title(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    slug = slug.strip("-")
    return slug


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
