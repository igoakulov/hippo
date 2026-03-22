from dataclasses import dataclass, field

from hippo.topics.topic import Topic


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
    topics: list[Topic] = field(default_factory=list)
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
            topics=[Topic.from_dict(n) for n in data.get("topics", [])],
        )
