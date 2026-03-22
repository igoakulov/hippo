from datetime import datetime

from hippo.parsers.chatgpt.models import Conversation, MessageNode


def format_timestamp(create_time: float) -> str:
    dt = datetime.fromtimestamp(create_time)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def message_to_markdown(msg: MessageNode, is_tool_invocation: bool = False) -> str:
    lines = []

    role_prefix = "USER" if msg.role == "user" else "ASSISTANT"

    lines.append(f"{role_prefix} · {msg.timestamp}")
    lines.append("")
    if is_tool_invocation:
        lines.append(msg.content)
    else:
        lines.append(msg.content)

    if msg.content_type == "code" and not is_tool_invocation:
        lang = msg.language if msg.language else ""
        content_lines = msg.content.split("\n")
        lines.append("")
        lines.append(f"```{lang}")
        lines.extend(content_lines)
        lines.append("```")

    return "\n".join(lines)


def build_siblings_map(messages: list[MessageNode]) -> dict[str, list[str]]:
    siblings: dict[str, list[str]] = {}
    current_parent_depth: list[tuple[str, str | None]] = []

    for i, msg in enumerate(messages):
        if i == 0:
            current_parent_depth = [(msg.id, None)]
            continue

        if msg.branch_depth == 0:
            current_parent_depth = [(msg.id, None)]
            continue

        if msg.branch_depth <= len(current_parent_depth):
            current_parent_depth = current_parent_depth[: msg.branch_depth]

        parent_at_depth = None
        for pid, _ in reversed(current_parent_depth):
            siblings_at_pid = siblings.get(pid, [])
            if len(siblings_at_pid) > 0:
                parent_at_depth = pid
                break

        if parent_at_depth:
            if parent_at_depth not in siblings:
                siblings[parent_at_depth] = []
            siblings[parent_at_depth].append(msg.id)

        current_parent_depth.append((msg.id, parent_at_depth))

    return siblings


def _build_tree_header(
    msg: MessageNode, siblings_map: dict[str, list[str]], ancestors: list[str]
) -> str:
    role_prefix = "USER" if msg.role == "user" else "ASSISTANT"

    if msg.branch_depth == 0:
        return f"{role_prefix} · {msg.timestamp}"

    prefix_parts: list[str] = []

    for ancestor in ancestors:
        sibling_list = siblings_map.get(ancestor, [])
        is_last_ancestor = msg.id in sibling_list and msg.id == sibling_list[-1]
        if is_last_ancestor:
            prefix_parts.append("    ")
        else:
            prefix_parts.append("│   ")

    parent_key = ancestors[-1] if ancestors else None
    sibling_list = siblings_map.get(parent_key, []) if parent_key else []
    is_last = msg.id in sibling_list and msg.id == sibling_list[-1]

    if is_last:
        prefix_parts.append("└── ")
    else:
        prefix_parts.append("├── ")

    return "".join(prefix_parts) + f"{role_prefix} · {msg.timestamp}"


def conversation_to_markdown(
    conv: Conversation,
    source_path: str | None,
    word_count: int,
    created_at: str,
    updated_at: str,
    last_message_id: str = "",
) -> str:
    siblings_map = build_siblings_map(conv.messages)

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
    if conv.sources:
        for source in conv.sources:
            lines.append(f"  - {source}")
    if last_message_id:
        lines.append(f"last_message_id: {last_message_id}")
    lines.append("---")
    lines.append("")

    ancestors: list[str] = []
    for msg in conv.messages:
        while len(ancestors) > msg.branch_depth:
            ancestors.pop()

        if msg.branch_depth > 0:
            if ancestors:
                parent = ancestors[-1]
                if parent not in siblings_map:
                    siblings_map[parent] = []
                if msg.id not in siblings_map[parent]:
                    siblings_map[parent].append(msg.id)
            else:
                root_id = conv.messages[0].id if conv.messages else msg.id
                if root_id not in siblings_map:
                    siblings_map[root_id] = []
                if msg.id not in siblings_map[root_id]:
                    siblings_map[root_id].append(msg.id)

    ancestors = []
    for msg in conv.messages:
        while len(ancestors) > msg.branch_depth:
            ancestors.pop()

        if msg.branch_depth > 0:
            if msg.branch_depth == 1:
                ancestors.append(conv.messages[0].id if conv.messages else msg.id)
            else:
                pass

        if msg.branch_depth == 0:
            header = (
                f"{'USER' if msg.role == 'user' else 'ASSISTANT'} · {msg.timestamp}"
            )
            content_lines = msg.content.split("\n")
            lines.append(header)
            lines.append("")
            if msg.content_type == "code" and not msg.is_tool_invocation:
                lines.append(f"```{msg.language or ''}")
                lines.extend(content_lines)
                lines.append("```")
            else:
                lines.append(msg.content)
        else:
            header = _build_tree_header(msg, siblings_map, ancestors)
            lines.append(header)
            lines.append("")
            lines.append(msg.content)

        lines.append("")
        lines.append("***")
        lines.append("")

        if msg.branch_depth > 0:
            if msg.branch_depth == 1:
                ancestors.append(msg.id)

    return "\n".join(lines).strip()
