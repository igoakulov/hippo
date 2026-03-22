import argparse

from hippo.cli.ingest import cmd_ingest_chat
from hippo.directories import VAULT_DIR
from hippo.sources.archive import get_source_stats
from hippo.topics.topic import get_frontmatter


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
