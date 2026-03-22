import argparse
import sys

from hippo.cli.utils import (
    SetMetadataResult,
    _count_connections,
    _print_errors,
    _print_warnings,
)
from hippo.graph import build_graph, sync as graph_sync, ValidationError
from hippo.topics import update_frontmatter, get_frontmatter


def cmd_topics(args: argparse.Namespace) -> None:
    if args.ids:
        topic_ids = [tid.strip() for tid in args.ids.split(",") if tid.strip()]
        if not topic_ids:
            print("ERROR: No topic ids provided", file=sys.stderr)
            sys.exit(1)

        if args.meta:
            result = _set_metadata(topic_ids, args.meta)
            if result.errors:
                print(f"Update failed: {len(result.errors)} errors\n")
                _print_errors(result.errors)
                sys.exit(1)
            if args.sync:
                result = graph_sync()
                if result.validation_errors:
                    print(f"Update failed: {len(result.validation_errors)} errors\n")
                    _print_errors(result.validation_errors)
                    sys.exit(1)
                connection_count = _count_connections(result.topics)
                print(
                    f"Sync complete: {len(result.topics)} topics, {connection_count} connections"
                )
        elif args.sync:
            result = graph_sync()
            if result.validation_errors:
                print(f"Sync failed: {len(result.validation_errors)} errors\n")
                _print_errors(result.validation_errors)
                sys.exit(1)
            _get_metadata(topic_ids)
        else:
            _get_metadata(topic_ids)
    else:
        result = build_graph()

        if result.validation_errors:
            print(f"Validation failed: {len(result.validation_errors)} errors\n")
            _print_errors(result.validation_errors)
            sys.exit(1)

        progress_counts: dict[str, int] = {}
        for topic in result.topics:
            prog = topic.progress or "new"
            progress_counts[prog] = progress_counts.get(prog, 0) + 1

        parts = []
        for prog in ["new", "started", "completed"]:
            if prog in progress_counts:
                parts.append(f"{progress_counts[prog]} {prog}")

        warning_count = len(result.clean_issues)
        summary = f"Total topics: {', '.join(parts)}, {warning_count} warnings"
        if warning_count > 0 and not args.warnings:
            summary += " (see --warnings)"
        print(summary)

        if args.warnings and result.clean_issues:
            print()
            _print_warnings(result.clean_issues)


def _get_metadata(topic_ids: list[str]) -> None:
    for i, topic_id in enumerate(topic_ids):
        fm = get_frontmatter(topic_id)
        if fm:
            if i > 0:
                print()
            print(f"{topic_id}.md")
            for key, value in fm.items():
                if value is None:
                    value = "null"
                elif isinstance(value, list):
                    value = str(value)
                print(f"{key}: {value}")
        else:
            print(f"ERROR: Topic not found: {topic_id}", file=sys.stderr)


def _set_metadata(topic_ids: list[str], set_fields: list[str]) -> SetMetadataResult:
    updates = {}
    for field in set_fields:
        if "=" not in field:
            print(
                f"ERROR: Invalid field format: {field} (expected key=value)",
                file=sys.stderr,
            )
            sys.exit(1)
        key, value = field.split("=", 1)
        updates[key.strip()] = _parse_value(value.strip())

    updated_count = 0
    errors: list[ValidationError] = []
    for topic_id in topic_ids:
        try:
            update_frontmatter(topic_id, updates)
            updated_count += 1
        except FileNotFoundError:
            errors.append(
                ValidationError(
                    topic_id=topic_id,
                    filename=f"{topic_id}.md",
                    message=f"Topic not found: {topic_id}",
                )
            )

    topic_str = "topic" if updated_count == 1 else "topics"
    print(f"Update complete: {updated_count} {topic_str}")
    return SetMetadataResult(updated_count=updated_count, errors=errors)


def _parse_value(value: str):
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].split(",")
        return [v.strip() for v in items if v.strip()]
    return value
