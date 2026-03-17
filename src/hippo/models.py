from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    title: str
    aliases: list[str] = field(default_factory=list)
    progress: str = "new"
    cluster: str = ""
    activity_score: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    sources: list[str] = field(default_factory=list)
    connections: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "aliases": self.aliases,
            "progress": self.progress,
            "cluster": self.cluster,
            "activity_score": self.activity_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sources": self.sources,
            "connections": self.connections,
        }

    @staticmethod
    def from_dict(data: dict) -> "Node":
        return Node(
            id=data["id"],
            title=data["title"],
            aliases=data.get("aliases", []),
            progress=data.get("progress", data.get("status", "new")),
            cluster=data.get("cluster", ""),
            activity_score=data.get("activity_score", 0.0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            sources=data.get("sources", []),
            connections=data.get("connections", data.get("relationships", {})),
        )


@dataclass
class Cluster:
    id: str
    title: str
    color: str = "#888888"

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


@dataclass
class Graph:
    topics: list[Node] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "clusters": [c.to_dict() for c in self.clusters],
            "topics": [n.to_dict() for n in self.topics],
        }

    @staticmethod
    def from_dict(data: dict) -> "Graph":
        return Graph(
            clusters=[Cluster.from_dict(c) for c in data.get("clusters", [])],
            topics=[
                Node.from_dict(n) for n in data.get("topics", data.get("nodes", []))
            ],
        )
