import argparse
import json
import sys
from collections import deque

from hippo.cli.utils import _count_connections, _print_errors, _print_warnings
from hippo.directories import get_graph_path
from hippo.graph_builder import sync as graph_sync

MINIMAL_FIELDS = frozenset({"id", "cluster", "parent", "related"})
FULL_FIELDS = frozenset(
    {
        "id",
        "title",
        "aliases",
        "progress",
        "created_at",
        "updated_at",
        "cluster",
        "parent",
        "related",
    }
)
FULL_PLUS_FIELDS = frozenset(
    {
        "id",
        "title",
        "aliases",
        "progress",
        "created_at",
        "updated_at",
        "cluster",
        "parent",
        "related",
        "sources",
        "word_count",
    }
)


def _project_fields(topics: list[dict], fields: frozenset | None) -> list[dict]:
    if fields is None:
        return topics
    return [{k: t.get(k) for k in fields} for t in topics]


def cmd_graph(args: argparse.Namespace) -> None:
    json_indent = 2 if args.pretty else None
    show_sync_summary = False

    field_set = None
    if hasattr(args, "full_plus") and args.full_plus:
        field_set = FULL_PLUS_FIELDS
    elif hasattr(args, "full") and args.full:
        field_set = FULL_FIELDS
    elif hasattr(args, "minimal") and args.minimal:
        field_set = MINIMAL_FIELDS
    else:
        field_set = MINIMAL_FIELDS

    if args.sync:
        result = graph_sync()
        if result.validation_errors:
            print(f"Sync failed: {len(result.validation_errors)} errors\n")
            _print_errors(result.validation_errors)
            sys.exit(1)
        connection_count = _count_connections(result.topics)
        warning_count = len(result.clean_issues)
        summary = f"Sync complete: {len(result.topics)} topics, {connection_count} connections"
        if warning_count > 0:
            summary += f", {warning_count} warnings"
            if not args.warnings:
                summary += " (see --warnings)"
        print(summary)
        if args.warnings and result.clean_issues:
            print()
            _print_warnings(result.clean_issues)
        show_sync_summary = True

    graph_path = get_graph_path()
    if not graph_path.exists():
        print("ERROR: Graph not found. Run 'hippo sync' first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(graph_path.read_text())
    topics = data.get("topics", [])

    if args.from_topic:
        _show_neighborhood(
            args.from_topic, topics, args.depth, args.to_topic, json_indent, field_set
        )
    else:
        if show_sync_summary:
            print()
        output_data = {
            "topics": _project_fields(topics, field_set),
            "clusters": data.get("clusters", []),
        }
        print(json.dumps(output_data, indent=json_indent))


def _build_connection_map(topics: list[dict]) -> dict[str, list[tuple]]:
    conn_map: dict[str, list[tuple]] = {}
    for topic in topics:
        topic_id = topic["id"]
        conn_map.setdefault(topic_id, [])
        if topic.get("parent"):
            parent = topic["parent"]
            conn_map[topic_id].append((parent, "parent"))
            conn_map.setdefault(parent, []).append((topic_id, "parent"))
        for related_id in topic.get("related", []):
            conn_map[topic_id].append((related_id, "related"))
            conn_map.setdefault(related_id, []).append((topic_id, "related"))
    return conn_map


def _show_neighborhood(
    from_id: str,
    topics: list,
    depth: int,
    to_id: str | None,
    json_indent: int | None = None,
    field_set: frozenset | None = None,
) -> None:
    topic_map = {t["id"]: t for t in topics}

    if from_id not in topic_map:
        print(f"ERROR: Topic not found: {from_id}", file=sys.stderr)
        sys.exit(1)

    if to_id:
        path = _find_path(from_id, to_id, topic_map)
        if path:
            reachable_ids = list(topic_map.keys())
            path_topics = _project_fields(
                [topic_map[tid] for tid in reachable_ids if tid in set(path)], field_set
            )
            print(json.dumps(path_topics, indent=json_indent))
        else:
            print(f"ERROR: No path from {from_id} to {to_id}", file=sys.stderr)
            sys.exit(1)
    else:
        reachable = _get_reachable(from_id, topic_map, topics, depth)
        reachable_topics = [topic_map[tid] for tid in reachable if tid in topic_map]
        print(
            json.dumps(_project_fields(reachable_topics, field_set), indent=json_indent)
        )


def _get_reachable(
    start_id: str, topic_map: dict, topics: list, max_depth: int
) -> set[str]:
    conn_map = _build_connection_map(topics)
    reachable = {start_id}
    frontier = {start_id}

    for _ in range(max_depth):
        new_frontier = set()
        for tid in frontier:
            for neighbor, _ in conn_map.get(tid, []):
                new_frontier.add(neighbor)
        new_frontier -= reachable
        if not new_frontier:
            break
        reachable |= new_frontier
        frontier = new_frontier

    return reachable


def _find_path(from_id: str, to_id: str, topic_map: dict) -> list[str] | None:
    conn_map = _build_connection_map(list(topic_map.values()))
    queue = deque([(from_id, [from_id])])
    visited = {from_id}

    while queue:
        current, path = queue.popleft()
        if current == to_id:
            return path

        for neighbor, conn_type in conn_map.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None
