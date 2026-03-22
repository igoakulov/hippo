import json
from pathlib import Path

from hippo.directories import get_backups_dir, get_graph_path, get_topic_path
from hippo.graph.cluster import get_clusters_path
from hippo.graph.validation import ValidationError


def validate_backup(timestamp: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    backups_dir = get_backups_dir()
    backup_path = backups_dir / f"graph_backup_{timestamp}.json"

    if not backup_path.exists():
        errors.append(
            ValidationError(
                topic_id="backup",
                filename="backup",
                message=f"Backup not found: {timestamp}",
            )
        )
        return errors

    try:
        backup_data = json.loads(backup_path.read_text())
    except json.JSONDecodeError:
        errors.append(
            ValidationError(
                topic_id="backup",
                filename="backup",
                message="Backup file is corrupted",
            )
        )
        return errors

    seen_ids: set[str] = set()
    for topic in backup_data.get("topics", []):
        topic_id = topic.get("id")
        if not topic_id:
            errors.append(
                ValidationError(
                    topic_id="backup",
                    filename="backup",
                    message="Missing topic id",
                )
            )
        elif topic_id in seen_ids:
            errors.append(
                ValidationError(
                    topic_id=topic_id,
                    filename="backup",
                    message=f"Duplicate topic id: {topic_id}",
                )
            )
        seen_ids.add(topic_id)

    return errors


def restore_backup(timestamp: str) -> bool:
    backups_dir = get_backups_dir()
    backup_path = backups_dir / f"graph_backup_{timestamp}.json"

    if not backup_path.exists():
        return False

    backup_data = json.loads(backup_path.read_text())
    graph_path = get_graph_path()

    graph_data = {
        "topics": backup_data["topics"],
        "clusters": backup_data["clusters"],
        "word_counts": backup_data.get("word_counts", {}),
    }
    graph_path.write_text(json.dumps(graph_data, indent=2))

    backup_clusters_path = backups_dir / f"clusters_backup_{timestamp}.json"

    clusters_path = get_clusters_path()
    if backup_clusters_path.exists():
        clusters_path.write_text(backup_clusters_path.read_text())
    else:
        from hippo.models import Cluster

        clusters = [Cluster.from_dict(c) for c in backup_data.get("clusters", [])]
        clusters_path.write_text(
            json.dumps({"clusters": [c.to_dict() for c in clusters]}, indent=2)
        )

    for topic_data in backup_data["topics"]:
        topic_id = topic_data["id"]
        _restore_topic_frontmatter(topic_id, topic_data)

    return True


def _restore_topic_frontmatter(topic_id: str, data: dict) -> None:
    from hippo.topics.topic import get_frontmatter_order

    path = get_topic_path(topic_id)
    if not path.exists():
        return

    lines = []
    lines.append("---")
    lines.append(f"id: {data['id']}")
    lines.append(f"title: {data['title']}")

    aliases = data.get("aliases", [])
    if aliases:
        lines.append("aliases:")
        for a in aliases:
            lines.append(f"  - {a}")
    else:
        lines.append("aliases:")

    lines.append(f"progress: {data.get('progress', 'new')}")
    lines.append(f"created_at: {data.get('created_at', '')}")
    lines.append(f"updated_at: {data.get('updated_at', '')}")
    lines.append(f"cluster: {data.get('cluster', '')}")
    lines.append(f"parent: {data.get('parent', '')}")

    related = data.get("related", [])
    if related:
        lines.append("related:")
        for r in related:
            lines.append(f"  - {r}")
    else:
        lines.append("related: []")

    sources = data.get("sources", [])
    if sources:
        lines.append("sources:")
        for s in sources:
            lines.append(f"  - {s}")
    else:
        lines.append("sources:")

    lines.append("---")

    content = path.read_text()
    body = ""
    if "---" in content:
        parts = content.split("---", 2)
        if len(parts) > 2:
            body = parts[2]

    path.write_text("\n".join(lines) + "\n" + body)
