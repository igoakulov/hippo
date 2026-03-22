import json
from datetime import datetime, timezone
from pathlib import Path

from hippo.directories import get_backups_dir, get_graph_path

DEFAULT_RETENTION = 20


def list_backups() -> list[str]:
    backups_dir = get_backups_dir()
    if not backups_dir.exists():
        return []
    backups = []
    for path in backups_dir.glob("graph_backup_*.json"):
        ts = path.stem.replace("graph_backup_", "")
        backups.append(ts)
    return sorted(backups, reverse=True)


def create_backup(result) -> Path:
    from hippo.graph.builder import save_graph
    from hippo.graph.cluster import get_clusters_path

    word_counts = save_graph(result)

    backups_dir = get_backups_dir()
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    backup_path = backups_dir / f"graph_backup_{timestamp}.json"

    clusters_path = get_clusters_path()
    backup_clusters_path = backups_dir / f"clusters_backup_{timestamp}.json"
    if clusters_path.exists():
        backup_clusters_path.write_text(clusters_path.read_text())

    backup_data = {
        "timestamp": timestamp,
        "topics": [t.to_dict() for t in result.topics],
        "clusters": [c.to_dict() for c in result.clusters],
        "word_counts": word_counts,
    }
    backup_path.write_text(json.dumps(backup_data, indent=2))

    _prune_backups()

    return backup_path


def _prune_backups(retention: int = DEFAULT_RETENTION) -> None:
    backups_dir = get_backups_dir()
    backups = sorted(
        backups_dir.glob("graph_backup_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old_backup in backups[retention:]:
        old_backup.unlink()
