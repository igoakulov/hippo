import json
from datetime import datetime

import click

from hippo.directories import ensure_directories, topic_file_exists
from hippo.models import Node
from hippo.node_markdown import delete_topic_file, save_topic
from hippo.storage import GraphStore


@click.group()
def main():
    """Hippo - Local-first knowledge graph for agent-driven research."""
    pass


@main.command()
def version():
    """Show version."""
    from hippo import __version__

    click.echo(__version__)


@main.group()
def topic():
    """Manage topics."""
    pass


@topic.command("add")
@click.option("--ids", required=True, help="Comma-separated topic IDs")
@click.option("--title", help="Title (defaults to ID)")
@click.option("--cluster", default="", help="Cluster assignment")
def topic_add(ids: str, title: str | None, cluster: str):
    """Add new topics."""
    store = GraphStore()
    store.load()

    for node_id in ids.split(","):
        node_id = node_id.strip()
        if not node_id:
            continue
        if store.get_node(node_id):
            click.echo(f"Topic '{node_id}' already exists", err=True)
            continue

        node_title = title if title else node_id.title()
        node = Node(
            id=node_id,
            title=node_title,
            cluster=cluster,
            created_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        store.add_node(node)
        save_topic(node)
        click.echo(f"Added topic: {node_id}")

    store.save()


@topic.command("update")
@click.option("--ids", help="Comma-separated topic IDs")
@click.option("--filter", "filter_expr", help="Filter expression (key=value)")
@click.option("--progress", help="Progress status")
@click.option("--cluster", help="Cluster assignment")
def topic_update(
    ids: str | None, filter_expr: str | None, progress: str | None, cluster: str | None
):
    """Update topics."""
    store = GraphStore()
    store.load()

    nodes = _get_filtered_nodes(store, ids, filter_expr)
    if not nodes:
        click.echo("No topics found", err=True)
        return

    for node in nodes:
        if progress:
            node.progress = progress
        if cluster is not None:
            node.cluster = cluster
        node.updated_at = datetime.utcnow().isoformat() + "Z"
        save_topic(node)
        click.echo(f"Updated topic: {node.id}")

    store.save()


@topic.command("delete")
@click.option("--ids", required=True, help="Comma-separated topic IDs")
def topic_delete(ids: str):
    """Delete topics."""
    store = GraphStore()
    store.load()

    for node_id in ids.split(","):
        node_id = node_id.strip()
        if not node_id:
            continue
        if not store.get_node(node_id):
            click.echo(f"Topic '{node_id}' not found", err=True)
            continue

        store.remove_node(node_id)
        delete_topic_file(node_id)
        click.echo(f"Deleted topic: {node_id}")

    store.save()


@topic.command("list")
@click.option("--cluster", help="Filter by cluster")
@click.option("--filter", "filter_expr", help="Filter expression")
def topic_list(cluster: str | None, filter_expr: str | None):
    """List topics."""
    store = GraphStore()
    store.load()

    nodes = _get_filtered_nodes(store, None, filter_expr)
    if cluster:
        nodes = [n for n in nodes if n.cluster == cluster]

    for node in nodes:
        click.echo(f"{node.id} - {node.title}")


@main.group()
def conn():
    """Manage connections between topics."""
    pass


@conn.command("add")
@click.argument("source")
@click.argument("target")
@click.option(
    "--type",
    "conn_type",
    default="parent",
    help="Connection type (parent, children, related)",
)
def conn_add(source: str, target: str, conn_type: str):
    """Add connection: hippo conn add source target --type parent"""
    store = GraphStore()
    store.load()

    source_node = store.get_node(source)
    if not source_node:
        click.echo(f"Topic '{source}' not found", err=True)
        return

    added = False
    for t in target.split(","):
        t = t.strip()
        if not t:
            continue
        if not store.get_node(t):
            click.echo(f"Target topic '{t}' not found", err=True)
            continue

        if t not in source_node.connections:
            source_node.connections[t] = []
        if conn_type not in source_node.connections[t]:
            source_node.connections[t].append(conn_type)
            added = True

    if added:
        source_node.updated_at = datetime.utcnow().isoformat() + "Z"
        save_topic(source_node)
        store.save()
        click.echo(f"Added connection: {source} -> {target} ({conn_type})")


@conn.command("remove")
@click.argument("source")
@click.argument("target", required=False)
@click.option("--all", "remove_all", is_flag=True, help="Remove all connections")
def conn_remove(source: str, target: str | None, remove_all: bool):
    """Remove connection: hippo conn remove source target"""
    store = GraphStore()
    store.load()

    source_node = store.get_node(source)
    if not source_node:
        click.echo(f"Topic '{source}' not found", err=True)
        return

    if remove_all:
        source_node.connections = {}
    elif target:
        if target in source_node.connections:
            del source_node.connections[target]
    else:
        click.echo("Specify target or --all", err=True)
        return

    source_node.updated_at = datetime.utcnow().isoformat() + "Z"
    save_topic(source_node)
    store.save()
    click.echo(f"Removed connections from: {source}")


@conn.command("list")
@click.argument("source")
def conn_list(source: str):
    """List connections: hippo conn list source"""
    store = GraphStore()
    store.load()

    source_node = store.get_node(source)
    if not source_node:
        click.echo(f"Topic '{source}' not found", err=True)
        return

    for target, types in source_node.connections.items():
        click.echo(f"{source} -> {target}: {', '.join(types)}")


@main.command()
@click.option("--cluster", help="Filter by cluster")
@click.option("--from", "from_node", help="Starting node")
@click.option("--depth", type=int, default=1, help="Traversal depth")
@click.option("--path", "path_node", help="Find path to target node")
def graph(
    cluster: str | None, from_node: str | None, depth: int, path_node: str | None
):
    """Query graph."""
    store = GraphStore()
    store.load()

    nodes = store.graph.topics

    if cluster:
        nodes = [n for n in nodes if n.cluster == cluster]

    if from_node:
        source = store.get_node(from_node)
        if not source:
            click.echo(f"Topic '{from_node}' not found", err=True)
            return
        related = _get_related_nodes(store, from_node, depth)
        nodes = [n for n in nodes if n.id in related]

    if path_node and from_node:
        paths = _find_all_paths(store, from_node, path_node)
        click.echo(json.dumps(paths, indent=2))
    else:
        click.echo(json.dumps([n.to_dict() for n in nodes], indent=2))


@main.command()
def sync():
    """Sync metadata from graph.json to all topic markdown files."""
    store = GraphStore()
    store.load()

    ensure_directories()

    for node in store.graph.topics:
        if not topic_file_exists(node.id):
            save_topic(node)
            click.echo(f"Created: {node.id}")
        else:
            save_topic(node)
            click.echo(f"Synced: {node.id}")

    click.echo("Sync complete")


def _get_filtered_nodes(
    store: GraphStore, ids: str | None, filter_expr: str | None
) -> list[Node]:
    if ids:
        node_list = []
        for node_id in ids.split(","):
            node = store.get_node(node_id.strip())
            if node:
                node_list.append(node)
        return node_list

    if filter_expr:
        filtered = []
        for part in filter_expr.split(","):
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip()
                value = value.strip()
                for node in store.graph.topics:
                    node_val = getattr(node, key, None)
                    if node_val and value in node_val:
                        filtered.append(node)
        return filtered

    return store.graph.topics


def _get_related_nodes(store: GraphStore, node_id: str, depth: int) -> set[str]:
    related = {node_id}
    queue = [(node_id, 0)]
    visited = {node_id}

    while queue:
        current, d = queue.pop(0)
        if d >= depth:
            continue

        node = store.get_node(current)
        if not node:
            continue

        for target in node.connections:
            if target not in visited:
                visited.add(target)
                related.add(target)
                queue.append((target, d + 1))

    return related


def _find_all_paths(store: GraphStore, start: str, end: str) -> list[list[str]]:
    """Find all paths between two nodes."""
    paths = []

    def dfs(current: str, path: list[str], visited: set[str]):
        if current == end:
            paths.append(path[:])
            return
        if current in visited:
            return

        visited.add(current)
        node = store.get_node(current)
        if node:
            for target in node.connections:
                path.append(target)
                dfs(target, path, visited)
                path.pop()
        visited.remove(current)

    dfs(start, [start], set())
    return paths


if __name__ == "__main__":
    main()
