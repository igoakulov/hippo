from pathlib import Path


def ensure_directories() -> None:
    dirs = [
        "sources/x_posts",
        "sources/conversations",
        "sources/local_files",
        "backups",
        "diffs",
        "logs",
        "render",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def get_topic_path(topic_id: str) -> Path:
    return Path(f"topics/{topic_id}.md")


def topic_file_exists(topic_id: str) -> bool:
    return get_topic_path(topic_id).exists()
