import re

from hippo.parsers.chatgpt.models import (
    EXCLUDE_CONTENT_TYPES,
    EXCLUDE_ROLES,
    INCLUDE_CONTENT_TYPES,
)


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

    text, _, _, _, _ = extract_content_with_attachments(msg)
    if not text or not text.strip():
        return False

    if text.strip() == "{}":
        return False

    return True


def extract_content_with_attachments(
    msg: dict,
) -> tuple[str, str, str, list[str], str | None]:
    content = msg.get("content", {})
    content_type = content.get("content_type", "")
    language = content.get("language", "")

    attachment_names: list[str] = []

    if content_type == "code":
        text = content.get("text", "")
    elif content_type == "multimodal_text":
        text, attachments = _extract_multimodal_text(msg)
        attachment_names = attachments
    else:
        parts = content.get("parts", [])
        text = "\n\n".join(str(p) for p in parts) if parts else ""

    metadata_attachments = msg.get("metadata", {}).get("attachments", [])
    for att in metadata_attachments:
        mime_type = att.get("mime_type", "")
        if mime_type.startswith("image/") or mime_type == "application/pdf":
            name = att.get("name", "")
            if name:
                attachment_names.append(f"[{name}]")

    audio_placeholder = _build_audio_placeholder(msg)

    return text, content_type, language, attachment_names, audio_placeholder


def _build_audio_placeholder(msg: dict) -> str | None:
    content = msg.get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        if isinstance(part, dict):
            part_type = part.get("content_type", "")

            if part_type == "audio_asset_pointer":
                duration = part.get("metadata", {}).get("end")
                format_str = part.get("format")

                if duration is not None and format_str:
                    return f"[audio_{duration}s.{format_str}]"
                elif duration is not None:
                    return f"[audio_{duration}s]"
                elif format_str:
                    return f"[audio.{format_str}]"
                else:
                    return "[audio]"

            elif part_type == "real_time_user_audio_video_asset_pointer":
                nested_audio = part.get("audio_asset_pointer", {})
                duration = nested_audio.get("metadata", {}).get("end")
                format_str = nested_audio.get("format")

                if duration is not None and format_str:
                    return f"[audio_{duration}s.{format_str}]"
                elif duration is not None:
                    return f"[audio_{duration}s]"
                elif format_str:
                    return f"[audio.{format_str}]"
                else:
                    return "[audio]"

    return None


def _extract_multimodal_text(msg: dict) -> tuple[str, list[str]]:
    content = msg.get("content", {})
    parts = content.get("parts", [])

    text_parts: list[str] = []

    for part in parts:
        if isinstance(part, dict):
            part_type = part.get("content_type", "")

            if part_type == "audio_transcription":
                audio_text = part.get("text", "")
                if audio_text:
                    text_parts.append(audio_text)

        elif isinstance(part, str) and part.strip():
            text_parts.append(part)

    text = "\n\n".join(text_parts) if text_parts else ""
    return text, []


def extract_content(msg: dict) -> tuple[str, str, str]:
    text, ct, lang, _, _ = extract_content_with_attachments(msg)
    return text, ct, lang


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)
