import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from hippo.cli.utils import _parse_iso_datetime
from hippo.directories import (
    get_chats_dir,
    get_chats_logs_dir,
    get_chat_log_path,
    VAULT_DIR,
)
from hippo.archive import add_reference, get_source_stats
from hippo.topic_markdown import get_frontmatter


def cmd_sources(args: argparse.Namespace) -> None:
    if args.ingest:
        cmd_ingest_chat(args)
        return

    stats = get_source_stats()
    orphan_sources = _find_orphan_sources()

    parts = []
    for type_name, count in stats["by_type"].items():
        parts.append(f"{count} {type_name}")

    warning_count = len(orphan_sources)
    summary = f"Total sources: {', '.join(parts)}, {stats['removed']} removed, {warning_count} warnings"
    if warning_count > 0 and not args.warnings:
        summary += " (see --warnings)"
    print(summary)

    if args.warnings and orphan_sources:
        print()
        _print_orphan_sources(orphan_sources)


def _print_orphan_sources(orphan_sources: list[str]) -> None:
    print("ORPHAN SOURCES:")
    for orphan in orphan_sources:
        print(f"- {orphan}")


def _find_orphan_sources() -> list[str]:
    sources_dir = VAULT_DIR / "sources"
    if not sources_dir.exists():
        return []

    all_sources_files: set[str] = set()
    for subdir in sources_dir.rglob("*"):
        if subdir.is_file():
            rel = subdir.relative_to(VAULT_DIR)
            all_sources_files.add(str(rel))

    referenced_sources: set[str] = set()
    topics_dir = VAULT_DIR / "topics"
    if topics_dir.exists():
        for topic_file in topics_dir.glob("*.md"):
            fm = get_frontmatter(topic_file.stem)
            if fm and fm.get("sources"):
                for src in fm.get("sources", []):
                    referenced_sources.add(src)

    orphan = all_sources_files - referenced_sources
    return sorted(orphan)


def _find_last_message_id_from_log(conv_id: str) -> str | None:
    logs_dir = get_chats_logs_dir()
    if not logs_dir.exists():
        return None
    for log_file in logs_dir.glob("ingest_*.json"):
        log_data = json.loads(log_file.read_text())
        for entry in log_data:
            if entry.get("conversation_id") == conv_id:
                return entry.get("last_message_id")
    return None


def cmd_ingest_chat(args: argparse.Namespace) -> None:
    from hippo.parsers.chatgpt import (
        load_conversations,
        filter_conversations,
        parse_conversation_expand,
        conversation_to_markdown,
        compute_word_count,
        get_last_message_id,
        get_output_filename,
        get_existing_file_for_conversation,
        message_to_markdown,
    )

    paths = [Path(p).expanduser().resolve() for p in args.paths]
    for path in paths:
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)

    from_time = None
    till_time = None
    titles = None

    if args.from_datetime:
        try:
            from_time = _parse_iso_datetime(args.from_datetime).timestamp()
        except ValueError:
            print(
                f"ERROR: Invalid --from datetime: {args.from_datetime}", file=sys.stderr
            )
            sys.exit(1)

    if args.till_datetime:
        try:
            till_time = _parse_iso_datetime(args.till_datetime).timestamp()
        except ValueError:
            print(
                f"ERROR: Invalid --till datetime: {args.till_datetime}", file=sys.stderr
            )
            sys.exit(1)

    if args.titles:
        titles = [t.strip() for t in args.titles.split(",") if t.strip()]

    conversations = []
    path_by_conv_id: dict[str, Path] = {}
    for path in paths:
        convs = load_conversations(path)
        for c in convs:
            conv_id = c.get("conversation_id") or c.get("id", "")
            path_by_conv_id[conv_id] = path
        conversations.extend(convs)

    filtered = filter_conversations(conversations, from_time, till_time, titles)

    chats_dir = get_chats_dir()
    logs_dir = get_chats_logs_dir()
    chats_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    updated_files = []
    filepath_changes = []

    log_entries = []
    ingest_timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    for conv_data in filtered:
        conv_id = conv_data.get("conversation_id") or conv_data.get("id", "")

        existing_file = get_existing_file_for_conversation(chats_dir, conv_id)
        existing_last_msg_id = None
        created_at = datetime.utcnow().isoformat()
        existing_body = ""

        if existing_file:
            existing_last_msg_id = _find_last_message_id_from_log(conv_id)
            existing_content = existing_file.read_text(encoding="utf-8")
            _, existing_body = _split_frontmatter(existing_content)
            created_at = _get_created_at_from_file(existing_file)

        conv = parse_conversation_expand(conv_data, existing_last_msg_id)

        if existing_file:
            new_output_filename = get_output_filename(conv)
            if existing_file.name != new_output_filename:
                filepath_changes.append((str(existing_file), new_output_filename))
                updated_files.append(new_output_filename)
            else:
                updated_files.append(str(existing_file))
        else:
            if conv.messages:
                created_files.append(get_output_filename(conv))
            else:
                continue

        output_filename = get_output_filename(conv)
        output_path = chats_dir / output_filename

        updated_at = datetime.utcnow().isoformat()
        last_msg_id = (
            get_last_message_id(conv) if conv.messages else (existing_last_msg_id or "")
        )

        if existing_file and existing_body.strip():
            existing_word_count = _get_word_count_from_file(existing_file)
            word_count = existing_word_count + compute_word_count(conv)

            body_content = existing_body.rstrip("\n")
            if conv.messages:
                if body_content:
                    body_content += "\n\n***\n\n"
                for msg in conv.messages:
                    body_content += message_to_markdown(msg)
                    body_content += "\n\n***\n\n"

            new_fm = _build_frontmatter(
                conv_id=conv_id,
                conv_title=conv.title,
                created_at=created_at,
                updated_at=updated_at,
                original_create_time=conv.create_time,
                word_count=word_count,
                urls=conv.sources,
            )
            content = new_fm + "\n" + body_content.rstrip()
        else:
            word_count = compute_word_count(conv)
            content = conversation_to_markdown(
                conv,
                source_path=None,
                word_count=word_count,
                created_at=created_at,
                updated_at=updated_at,
            )

        output_path.write_text(content, encoding="utf-8")

        log_entries.append(
            {
                "conversation_id": conv_id,
                "output_file": str(output_path),
                "last_message_id": last_msg_id,
                "ingested_at": ingest_timestamp,
                "filters": {
                    "from": args.from_datetime,
                    "till": args.till_datetime,
                    "titles": args.titles,
                },
            }
        )

    if log_entries:
        log_path = get_chat_log_path(ingest_timestamp)
        log_path.write_text(json.dumps(log_entries, indent=2), encoding="utf-8")

    for entry in log_entries:
        add_reference("chat", entry["output_file"], [])

    total_created = len(created_files)
    total_updated = len(updated_files)
    print(f"Ingest complete: {total_created} created, {total_updated} updated")

    if filepath_changes:
        print("\nWARNING: Update chat file titles in topic sources:")
        for old_path, new_filename in filepath_changes:
            print(f"- {old_path} -> {new_filename}")


def _get_created_at_from_file(file_path: Path) -> str:
    try:
        content = file_path.read_text(encoding="utf-8")
        pattern = re.compile(r"^created_at:\s*(.+)$", re.MULTILINE)
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return datetime.utcnow().isoformat()


def _get_word_count_from_file(file_path: Path) -> int:
    try:
        content = file_path.read_text(encoding="utf-8")
        pattern = re.compile(r"^word_count:\s*(\d+)$", re.MULTILINE)
        match = pattern.search(content)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 0


def _split_frontmatter(content: str) -> tuple[dict, str]:
    fm_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = fm_pattern.search(content)
    if match:
        fm_text = match.group(1)
        body = content[match.end() :]
        body = body.lstrip("\n")
        fm = {}
        for line in fm_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                fm[key.strip()] = value.strip()
        return fm, body
    return {}, content


def _build_frontmatter(
    conv_id: str,
    conv_title: str,
    created_at: str,
    updated_at: str,
    original_create_time: float,
    word_count: int,
    urls: list[str],
) -> str:
    from hippo.parsers.chatgpt import format_timestamp

    lines = ["---"]
    lines.append(f"id: {conv_id}")
    lines.append(f"title: {conv_title}")
    lines.append(f"created_at: {created_at}")
    lines.append(f"updated_at: {updated_at}")
    lines.append(
        f"original_conversation_created_at: {format_timestamp(original_create_time)}"
    )
    lines.append(f"word_count: {word_count}")
    lines.append("sources:")
    for url in urls:
        lines.append(f"  - {url}")
    lines.append("---")
    return "\n".join(lines)
