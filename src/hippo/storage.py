import json
from pathlib import Path

from hippo.models import Cluster, Graph, Topic


class GraphStore:
    def __init__(self, graph_path: str | None = None):
        self._graph_path = Path(graph_path) if graph_path else None
        self._graph: Graph | None = None

    def _require_loaded(self) -> Graph:
        if self._graph is None:
            raise RuntimeError("Graph not loaded. Call load() first.")
        return self._graph

    @property
    def graph(self) -> Graph:
        return self._require_loaded()

    def load(self) -> None:
        if self._graph_path and self._graph_path.exists():
            data = json.loads(self._graph_path.read_text())
            self._graph = Graph.from_dict(data)
        else:
            self._graph = Graph()

    def save(self) -> None:
        if not self._graph_path:
            return
        g = self._require_loaded()
        self._graph_path.parent.mkdir(parents=True, exist_ok=True)
        self._graph_path.write_text(json.dumps(g.to_dict(), indent=2))

    def get_topic(self, topic_id: str) -> Topic | None:
        g = self._require_loaded()
        for topic in g.topics:
            if topic.id == topic_id:
                return topic
        return None

    def add_topic(self, topic: Topic) -> None:
        g = self._require_loaded()
        g.topics.append(topic)

    def remove_topic(self, topic_id: str) -> None:
        g = self._require_loaded()
        g.topics = [n for n in g.topics if n.id != topic_id]
        for topic in g.topics:
            if topic.parent == topic_id:
                topic.parent = ""

    def list_topics(self, cluster: str | None = None) -> list[Topic]:
        g = self._require_loaded()
        if cluster:
            return [n for n in g.topics if n.cluster == cluster]
        return g.topics

    def get_cluster(self, cluster_id: str) -> Cluster | None:
        g = self._require_loaded()
        for cluster in g.clusters:
            if cluster.id == cluster_id:
                return cluster
        return None

    def add_cluster(self, cluster: Cluster) -> None:
        g = self._require_loaded()
        g.clusters.append(cluster)

    def list_clusters(self) -> list[Cluster]:
        g = self._require_loaded()
        return g.clusters
