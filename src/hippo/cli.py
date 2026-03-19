import argparse
import json
import sys
from pathlib import Path

from hippo import __version__
from hippo.config import init_vault
from hippo.graph_builder import sync as graph_sync
from hippo.topic_markdown import update_frontmatter, get_frontmatter


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


def cmd_sync(args: argparse.Namespace) -> None:
    result = graph_sync()
    for topic in result.topics:
        print(f"Synced: {topic.id}")
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    print(f"Sync complete: {len(result.topics)} topics, {len(result.edges)} edges")


def cmd_meta(args: argparse.Namespace) -> None:
    topic_ids = [tid.strip() for tid in args.ids.split(",") if tid.strip()]
    if not topic_ids:
        print("Error: No topic IDs provided", file=sys.stderr)
        sys.exit(1)

    if args.set_fields:
        _set_metadata(topic_ids, args.set_fields)
    else:
        _get_metadata(topic_ids)


def _get_metadata(topic_ids: list[str]) -> None:
    for topic_id in topic_ids:
        fm = get_frontmatter(topic_id)
        if fm:
            print(f"--- {topic_id} ---")
            for key, value in fm.items():
                print(f"  {key}: {value}")
            print()
        else:
            print(f"Topic not found: {topic_id}", file=sys.stderr)


def _set_metadata(topic_ids: list[str], set_fields: list[str]) -> None:
    updates = {}
    for field in set_fields:
        if "=" not in field:
            print(
                f"Error: Invalid field format: {field} (expected key=value)",
                file=sys.stderr,
            )
            sys.exit(1)
        key, value = field.split("=", 1)
        updates[key.strip()] = _parse_value(value.strip())

    for topic_id in topic_ids:
        try:
            update_frontmatter(topic_id, updates)
            print(f"Updated: {topic_id}")
        except FileNotFoundError:
            print(f"Topic not found: {topic_id}", file=sys.stderr)


def _parse_value(value: str):
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].split(",")
        return [v.strip() for v in items if v.strip()]
    return value


def cmd_graph(args: argparse.Namespace) -> None:
    from hippo.directories import get_graph_path

    graph_path = get_graph_path()
    if not graph_path.exists():
        print("Graph not found. Run 'hippo sync' first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(graph_path.read_text())
    topics = data.get("topics", [])
    edges = data.get("edges", [])

    if args.from_topic:
        _show_neighborhood(args.from_topic, topics, edges, args.depth, args.to_topic)
    else:
        print(json.dumps(data, indent=2))


def _show_neighborhood(
    from_id: str, topics: list, edges: list, depth: int, to_id: str | None
) -> None:
    topic_map = {t["id"]: t for t in topics}

    if from_id not in topic_map:
        print(f"Topic not found: {from_id}", file=sys.stderr)
        sys.exit(1)

    if to_id:
        path = _find_path(from_id, to_id, topic_map, edges)
        if path:
            print(" → ".join(path))
        else:
            print("No path found", file=sys.stderr)
            sys.exit(1)
    else:
        reachable = _get_reachable(from_id, topic_map, edges, depth)
        print(
            json.dumps(
                [topic_map[tid] for tid in reachable if tid in topic_map], indent=2
            )
        )


def _get_reachable(
    start_id: str, topic_map: dict, edges: list, max_depth: int
) -> set[str]:
    reachable = {start_id}
    frontier = {start_id}

    for _ in range(max_depth):
        new_frontier = set()
        for tid in frontier:
            for edge in edges:
                if edge["source"] == tid:
                    new_frontier.add(edge["target"])
                elif edge["target"] == tid:
                    new_frontier.add(edge["source"])
        new_frontier -= reachable
        if not new_frontier:
            break
        reachable |= new_frontier
        frontier = new_frontier

    return reachable


def _find_path(
    from_id: str, to_id: str, topic_map: dict, edges: list
) -> list[str] | None:
    from collections import deque

    edge_map: dict[str, list[tuple]] = {}
    for edge in edges:
        edge_map.setdefault(edge["source"], []).append((edge["target"], edge["type"]))
        edge_map.setdefault(edge["target"], []).append((edge["source"], edge["type"]))

    queue = deque([(from_id, [from_id])])
    visited = {from_id}

    while queue:
        current, path = queue.popleft()
        if current == to_id:
            return path

        for neighbor, edge_type in edge_map.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [f"{neighbor} ({edge_type})"]))

    return None


def cmd_clean(args: argparse.Namespace) -> None:
    result = graph_sync()
    if result.clean_issues:
        for issue in result.clean_issues:
            print(f"[{issue.issue_type}] {issue.topic_id}: {issue.message}")
        sys.exit(1)
    else:
        print("No issues found")


def cmd_backup(args: argparse.Namespace) -> None:
    from hippo.backup import create_backup

    result = graph_sync()
    backup_path = create_backup(result)
    print(f"Backup created: {backup_path}")


def cmd_restore(args: argparse.Namespace) -> None:
    from hippo.backup import restore_backup, list_backups

    if args.version:
        success = restore_backup(args.version)
    else:
        backups = list_backups()
        if not backups:
            print("No backups found", file=sys.stderr)
            sys.exit(1)
        success = restore_backup(backups[0])

    if success:
        print("Restore complete")
        graph_sync()
    else:
        print("Restore failed", file=sys.stderr)
        sys.exit(1)


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
    sync_parser.set_defaults(func=cmd_sync)

    meta_parser = subparsers.add_parser("meta", help="Get or set topic metadata")
    meta_parser.add_argument("--ids", required=True, help="Comma-separated topic IDs")
    meta_parser.add_argument(
        "--set", nargs="+", dest="set_fields", help="field=value pairs"
    )
    meta_parser.set_defaults(func=cmd_meta)

    graph_parser = subparsers.add_parser("graph", help="View graph")
    graph_parser.add_argument("--from", dest="from_topic", help="Starting topic")
    graph_parser.add_argument("--depth", type=int, default=1, help="Traversal depth")
    graph_parser.add_argument("--to", dest="to_topic", help="Target topic for path")
    graph_parser.set_defaults(func=cmd_graph)

    clean_parser = subparsers.add_parser("clean", help="Maintenance check")
    clean_parser.set_defaults(func=cmd_clean)

    backup_parser = subparsers.add_parser("backup", help="Create rolling backup")
    backup_parser.set_defaults(func=cmd_backup)

    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("--version", help="Specific backup version")
    restore_parser.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
