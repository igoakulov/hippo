import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Diff:
    timestamp: str
    topics_added: list[dict] = field(default_factory=list)
    topics_deleted: list[str] = field(default_factory=list)
    topics_metadata_changed: dict[str, dict[str, dict]] = field(default_factory=dict)
    topics_content_changed: dict[str, dict[str, int | str]] = field(
        default_factory=dict
    )
    connections_added: list[dict] = field(default_factory=list)
    connections_deleted: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "topics": {
                "added": self.topics_added,
                "deleted": self.topics_deleted,
                "metadata_changed": self.topics_metadata_changed,
                "content_changed": self.topics_content_changed,
            },
            "connections": {
                "added": self.connections_added,
                "deleted": self.connections_deleted,
            },
        }

    @staticmethod
    def from_dict(data: dict) -> "Diff":
        topics = data.get("topics", {})
        connections = data.get("connections", {})
        return Diff(
            timestamp=data.get("timestamp", ""),
            topics_added=topics.get("added", []),
            topics_deleted=topics.get("deleted", []),
            topics_metadata_changed=topics.get("metadata_changed", {}),
            topics_content_changed=topics.get("content_changed", {}),
            connections_added=connections.get("added", []),
            connections_deleted=connections.get("deleted", []),
        )

    def is_empty(self) -> bool:
        return (
            not self.topics_added
            and not self.topics_deleted
            and not self.topics_metadata_changed
            and not self.topics_content_changed
            and not self.connections_added
            and not self.connections_deleted
        )


def _delta_str(old: int, new: int) -> str:
    diff = new - old
    if diff > 0:
        return f"+{diff}"
    return str(diff)


def compute_diff(
    old_graph: dict | None,
    new_graph: dict,
) -> Diff:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    old_topics = {
        t["id"]: t for t in (old_graph.get("topics", []) if old_graph else [])
    }
    new_topics = {t["id"]: t for t in new_graph.get("topics", [])}

    topics_added: list[dict] = []
    topics_deleted: list[str] = []
    topics_metadata_changed: dict[str, dict[str, dict]] = {}
    topics_content_changed: dict[str, dict[str, int | str]] = {}
    connections_added: list[dict] = []
    connections_deleted: list[dict] = []

    for topic_id, new_topic in new_topics.items():
        if topic_id not in old_topics:
            topics_added.append(new_topic)
        else:
            old_topic = old_topics[topic_id]
            changed: dict[str, dict] = {}
            for key in (
                "parent",
                "related",
                "cluster",
                "sources",
                "progress",
                "aliases",
                "title",
            ):
                old_val = old_topic.get(key)
                new_val = new_topic.get(key)
                if old_val != new_val:
                    changed[key] = {"old": old_val, "new": new_val}
                    if key == "parent":
                        if old_val:
                            connections_deleted.append(
                                {
                                    "source": topic_id,
                                    "target": old_val,
                                    "type": "parent",
                                }
                            )
                        if new_val:
                            connections_added.append(
                                {
                                    "source": topic_id,
                                    "target": new_val,
                                    "type": "parent",
                                }
                            )
                    elif key == "related":
                        old_related = set(old_val or [])
                        new_related = set(new_val or [])
                        for r in old_related - new_related:
                            connections_deleted.append(
                                {"source": topic_id, "target": r, "type": "related"}
                            )
                        for r in new_related - old_related:
                            connections_added.append(
                                {"source": topic_id, "target": r, "type": "related"}
                            )
            if changed:
                topics_metadata_changed[topic_id] = changed

            old_wc = old_topics.get(topic_id, {}).get("word_count", 0)
            new_wc = new_topic.get("word_count", 0)
            if old_wc != new_wc:
                topics_content_changed[topic_id] = {
                    "old": old_wc,
                    "new": new_wc,
                    "delta": _delta_str(old_wc, new_wc),
                }

    for topic_id in old_topics:
        if topic_id not in new_topics:
            topics_deleted.append(topic_id)
            old_topic = old_topics[topic_id]
            if old_topic.get("parent"):
                connections_deleted.append(
                    {
                        "source": topic_id,
                        "target": old_topic["parent"],
                        "type": "parent",
                    }
                )
            for r in old_topic.get("related", []):
                connections_deleted.append(
                    {"source": topic_id, "target": r, "type": "related"}
                )

    return Diff(
        timestamp=timestamp,
        topics_added=topics_added,
        topics_deleted=topics_deleted,
        topics_metadata_changed=topics_metadata_changed,
        topics_content_changed=topics_content_changed,
        connections_added=connections_added,
        connections_deleted=connections_deleted,
    )


def save_diff(diff: Diff) -> Path:
    from hippo.directories import get_diffs_dir

    diffs_dir = get_diffs_dir()
    diffs_dir.mkdir(parents=True, exist_ok=True)
    diff_path = diffs_dir / f"diff_{diff.timestamp}.json"
    diff_path.write_text(json.dumps(diff.to_dict(), indent=2))
    return diff_path


def load_diffs() -> list[Diff]:
    from hippo.directories import get_diffs_dir

    diffs_dir = get_diffs_dir()
    if not diffs_dir.exists():
        return []
    diffs = []
    for path in sorted(diffs_dir.glob("diff_*.json")):
        data = json.loads(path.read_text())
        diffs.append(Diff.from_dict(data))
    return diffs
