from hippo.directories import get_topic_path
from hippo.models import Node


def _format_connections(connections: dict[str, list[str]]) -> str:
    parts = []
    for rel_type, targets in connections.items():
        if targets:
            parts.append(f"{rel_type}:{','.join(targets)}")
    return ";".join(parts)


def node_to_markdown(node: Node) -> str:
    conn_str = _format_connections(node.connections)
    lines = [
        f"id: {node.id}",
        f"title: {node.title}",
        f"aliases: {','.join(node.aliases)}",
        f"progress: {node.progress}",
        f"cluster: {node.cluster}",
        f"created: {node.created_at[:10] if node.created_at else ''}",
        f"updated: {node.updated_at[:10] if node.updated_at else ''}",
        f"sources: {','.join(node.sources)}",
        f"connections: {conn_str}",
        "",
        f"# {node.title}",
        "",
    ]
    return "\n".join(lines)


def node_from_markdown(node_id: str, content: str) -> Node:
    lines = content.split("\n")
    data = {}
    body_lines = []
    in_body = False

    for line in lines:
        if in_body:
            body_lines.append(line)
        elif line.startswith("id:"):
            data["id"] = line.split(":", 1)[1].strip()
        elif line.startswith("title:"):
            data["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("aliases:"):
            aliases_str = line.split(":", 1)[1].strip()
            data["aliases"] = [a.strip() for a in aliases_str.split(",") if a.strip()]
        elif line.startswith("progress:"):
            data["progress"] = line.split(":", 1)[1].strip()
        elif line.startswith("cluster:"):
            data["cluster"] = line.split(":", 1)[1].strip()
        elif line.startswith("created:"):
            data["created_at"] = line.split(":", 1)[1].strip()
        elif line.startswith("updated:"):
            data["updated_at"] = line.split(":", 1)[1].strip()
        elif line.startswith("sources:"):
            sources_str = line.split(":", 1)[1].strip()
            data["sources"] = [s.strip() for s in sources_str.split(",") if s.strip()]
        elif line.startswith("connections:") or line.startswith("relationships:"):
            conn_str = line.split(":", 1)[1].strip()
            connections = {}
            if conn_str:
                for part in conn_str.split(";"):
                    if ":" in part:
                        rel_type, targets = part.split(":", 1)
                        connections[rel_type] = [
                            t.strip() for t in targets.split(",") if t.strip()
                        ]
            data["connections"] = connections
        elif line.startswith("# "):
            in_body = True
            body_lines.append(line)

    return Node(
        id=data.get("id", node_id),
        title=data.get("title", ""),
        aliases=data.get("aliases", []),
        progress=data.get("progress", data.get("status", "new")),
        cluster=data.get("cluster", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        sources=data.get("sources", []),
        connections=data.get("connections", data.get("relationships", {})),
    )


def save_topic(node: Node) -> None:
    path = get_topic_path(node.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(node_to_markdown(node))


def load_topic(node_id: str) -> Node | None:
    path = get_topic_path(node_id)
    if not path.exists():
        return None
    return node_from_markdown(node_id, path.read_text())


def delete_topic_file(node_id: str) -> None:
    path = get_topic_path(node_id)
    if path.exists():
        path.unlink()
