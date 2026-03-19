from pathlib import Path

VAULT_DIR = Path.cwd()
HIPPO_DIR = VAULT_DIR / ".hippo"


def get_topic_path(topic_id: str) -> Path:
    return VAULT_DIR / "topics" / f"{topic_id}.md"


def topic_file_exists(topic_id: str) -> bool:
    return get_topic_path(topic_id).exists()


def get_hippo_dir() -> Path:
    return HIPPO_DIR


def get_backups_dir() -> Path:
    return HIPPO_DIR / "backups"


def get_diffs_dir() -> Path:
    return HIPPO_DIR / "diffs"


def get_graph_path() -> Path:
    return HIPPO_DIR / "graph.json"


def get_clusters_path() -> Path:
    return HIPPO_DIR / "clusters.json"
