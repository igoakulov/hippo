import re

from hippo.parsers.chatgpt.models import Conversation, MessageNode
from hippo.parsers.chatgpt.extract import (
    extract_content_with_attachments,
    extract_urls,
    should_include_message,
)
from hippo.parsers.chatgpt.format import format_timestamp
from hippo.parsers.chatgpt.transform import _clean_url, _transform_content


def _is_tool_invocation(msg: dict) -> bool:
    if msg.get("content", {}).get("content_type") == "code":
        text = msg.get("content", {}).get("text", "")
        if re.match(r"^\w+\(.+\)$", text.strip()):
            return True
    return False


def _format_tool_invocation(msg: dict) -> str:
    text = msg.get("content", {}).get("text", "")
    match = re.match(r"^(\w+)\((.*)\)$", text.strip(), re.DOTALL)
    if match:
        tool_name = match.group(1)
        args = match.group(2).strip()
        args = args.strip('"').strip("'")
        return f"[{tool_name}: {args}]"
    return text


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
    sources: list[str] = []

    if root:
        _traverse_messages(
            mapping, root, None, messages, sources, branch_depth=0, first_branch=True
        )

    return Conversation(
        id=conv_id,
        title=title,
        create_time=create_time,
        messages=messages,
        sources=sources,
    )


def _traverse_messages(
    mapping: dict,
    node_id: str,
    parent_id: str | None,
    messages: list[MessageNode],
    sources: list[str],
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
        content, content_type, language, attachment_names, audio_placeholder = (
            extract_content_with_attachments(msg)
        )
        create_time = msg.get("create_time") or 0
        is_tool = _is_tool_invocation(msg)

        if content or attachment_names or audio_placeholder or is_tool:
            if is_tool:
                final_content = _format_tool_invocation(msg)
                message_urls = extract_urls(final_content)
                for url in message_urls:
                    cleaned = _clean_url(url)
                    if cleaned not in sources:
                        sources.append(cleaned)
            else:
                content = _transform_content(content, msg)

                message_urls = extract_urls(content)
                for url in message_urls:
                    cleaned = _clean_url(url)
                    if cleaned not in sources:
                        sources.append(cleaned)

                _collect_search_urls(msg, sources)
                _collect_attachment_filenames(attachment_names, sources)

                prefix_parts: list[str] = []
                if audio_placeholder:
                    prefix_parts.append(audio_placeholder)
                prefix_parts.extend(attachment_names)

                final_content = content
                if prefix_parts:
                    prefix = "\n".join(prefix_parts)
                    if final_content:
                        final_content = f"{prefix}\n\n{final_content}"
                    else:
                        final_content = prefix

            messages.append(
                MessageNode(
                    id=node_id,
                    role=msg["author"]["role"],
                    content=final_content,
                    timestamp=format_timestamp(create_time),
                    content_type=content_type,
                    language=language,
                    branch_depth=branch_depth,
                    is_tool_invocation=is_tool,
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
                mapping, child_id, node_id, messages, sources, child_branch_depth, first
            )
            if child_last:
                last_msg_id = child_last

    return last_msg_id


def _collect_search_urls(msg: dict, sources: list[str]) -> None:
    search_groups = msg.get("metadata", {}).get("search_result_groups", [])
    for group in search_groups:
        for entry in group.get("entries", []):
            url = entry.get("url", "")
            if url:
                url = _clean_url(url)
                if url not in sources:
                    sources.append(url)

    content_refs = msg.get("metadata", {}).get("content_references", [])
    for ref in content_refs:
        ref_type = ref.get("type", "")
        if ref_type in ("grouped_webpages", "link_title"):
            url = ref.get("url", "")
            if url:
                url = _clean_url(url)
                if url not in sources:
                    sources.append(url)


def _collect_attachment_filenames(
    attachment_names: list[str], sources: list[str]
) -> None:
    for name in attachment_names:
        clean_name = name.strip("[]")
        if clean_name and clean_name not in sources:
            sources.append(clean_name)


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
