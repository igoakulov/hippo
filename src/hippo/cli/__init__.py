import argparse
import sys
from pathlib import Path

from hippo import __version__
from hippo.config import init_vault

from .backup import cmd_backup, cmd_restore
from .graph import cmd_graph
from .sources import cmd_sources
from .sync import cmd_sync
from .topics import cmd_topics


def cmd_init(args: argparse.Namespace) -> None:
    vault_path = Path(args.vault).expanduser().resolve()
    try:
        init_vault(vault_path)
        print(f"Initialized vault at: {vault_path}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_version(args: argparse.Namespace) -> None:
    print(__version__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hippo",
        description="Hippo - Local-first knowledge graph for agent-driven research.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new vault")
    init_parser.add_argument("--vault", required=True, help="Path to vault directory")
    init_parser.set_defaults(func=cmd_init)

    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)

    sync_parser = subparsers.add_parser("sync", help="Rebuild graph from files")
    sync_parser.add_argument("--warnings", action="store_true", help="Show warnings")
    sync_parser.set_defaults(func=cmd_sync)

    topics_parser = subparsers.add_parser("topics", help="List or update topics")
    topics_parser.add_argument("--ids", help="Comma-separated topic IDs")
    topics_parser.add_argument("--meta", nargs="+", help="field=value pairs to set")
    topics_parser.add_argument(
        "--sync", action="store_true", help="Sync graph after update"
    )
    topics_parser.add_argument("--warnings", action="store_true", help="Show warnings")
    topics_parser.set_defaults(func=cmd_topics)

    graph_parser = subparsers.add_parser("graph", help="View graph")
    graph_parser.add_argument("--from", dest="from_topic", help="Starting topic")
    graph_parser.add_argument("--depth", type=int, default=1, help="Traversal depth")
    graph_parser.add_argument("--to", dest="to_topic", help="Target topic for path")
    graph_parser.add_argument(
        "--sync", action="store_true", help="Sync graph before viewing"
    )
    graph_parser.add_argument("--warnings", action="store_true", help="Show warnings")
    field_group = graph_parser.add_mutually_exclusive_group()
    field_group.add_argument(
        "--minimal",
        action="store_true",
        help="Minimal fields: id, cluster, parent, related (default)",
    )
    field_group.add_argument(
        "--full", action="store_true", help="Full fields: all standard fields"
    )
    field_group.add_argument(
        "--full+",
        dest="full_plus",
        action="store_true",
        help="Full+ fields: full + sources, word_count",
    )
    format_group = graph_parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--compact",
        action="store_true",
        default=True,
        help="Compact JSON output (default)",
    )
    format_group.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    graph_parser.set_defaults(func=cmd_graph)

    backup_parser = subparsers.add_parser("backup", help="Create rolling backup")
    backup_parser.add_argument("--warnings", action="store_true", help="Show warnings")
    backup_parser.set_defaults(func=cmd_backup)

    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("--version", help="Specific backup version")
    restore_parser.set_defaults(func=cmd_restore)

    sources_parser = subparsers.add_parser("sources", help="Manage sources")
    sources_parser.add_argument("--warnings", action="store_true", help="Show warnings")
    sources_parser.add_argument(
        "--ingest",
        choices=["chatgpt"],
        help="Ingest source (e.g., chatgpt)",
    )
    sources_parser.add_argument("--path", help="Path to conversations.json or archive")
    sources_parser.add_argument(
        "--from", dest="from_datetime", help="Start datetime (ISO 8601)"
    )
    sources_parser.add_argument(
        "--till", dest="till_datetime", help="End datetime (ISO 8601)"
    )
    sources_parser.add_argument("--titles", help="Filter by titles (comma-separated)")
    sources_parser.set_defaults(func=cmd_sources)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
