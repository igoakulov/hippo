import json
from dataclasses import dataclass
from pathlib import Path


def get_clusters_path() -> Path:
    from hippo.directories import get_hippo_dir

    return get_hippo_dir() / "clusters.json"


def save_clusters(clusters: list["Cluster"]) -> None:
    path = get_clusters_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"clusters": [c.to_dict() for c in clusters]}
    path.write_text(json.dumps(data, indent=2))


def load_clusters() -> list["Cluster"]:
    path = get_clusters_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return [Cluster.from_dict(c) for c in data.get("clusters", [])]
    except (json.JSONDecodeError, IOError):
        return []


def merge_clusters(inferred: list["Cluster"]) -> list["Cluster"]:
    existing = {c.id: c for c in load_clusters()}
    result: list[Cluster] = []
    for cluster in inferred:
        if cluster.id in existing:
            result.append(existing[cluster.id])
        else:
            result.append(cluster)
    return result


PALETTE = [
    "#4A90D9",
    "#50C878",
    "#FF6B6B",
    "#FFD93D",
    "#6BCB77",
    "#4D96FF",
    "#FF922B",
    "#845EC2",
    "#00C9A7",
    "#F9F871",
    "#FFB3BA",
    "#BAFFC9",
    "#BAE1FF",
    "#FFFFBA",
    "#FFD1DC",
    "#C9B1FF",
    "#FF9F1C",
    "#2EC4B6",
    "#E71D36",
    "#011627",
    "#FDFFFC",
    "#011627",
    "#2EC4B6",
    "#FF9F1C",
    "#E71D36",
    "#7209B7",
    "#3A0CA3",
    "#4CC9F0",
    "#F72585",
    "#4361EE",
]


@dataclass
class Cluster:
    id: str
    title: str
    color: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "color": self.color,
        }

    @staticmethod
    def from_dict(data: dict) -> "Cluster":
        return Cluster(
            id=data["id"],
            title=data["title"],
            color=data.get("color", "#888888"),
        )


def infer_clusters(topics: list[dict]) -> list[Cluster]:
    unique_clusters: set[str] = set()
    for topic in topics:
        cluster_id = topic.get("cluster", "")
        if cluster_id:
            unique_clusters.add(cluster_id)

    clusters = []
    for i, cluster_id in enumerate(sorted(unique_clusters)):
        color = PALETTE[i % len(PALETTE)]
        title = _format_cluster_title(cluster_id)
        clusters.append(Cluster(id=cluster_id, title=title, color=color))

    return clusters


def _format_cluster_title(cluster_id: str) -> str:
    words = cluster_id.replace("-", " ").replace("_", " ").split()
    return " ".join(word.capitalize() for word in words)


def get_cluster_color(cluster_id: str, clusters: list[Cluster]) -> str | None:
    for cluster in clusters:
        if cluster.id == cluster_id:
            return cluster.color
    return None
