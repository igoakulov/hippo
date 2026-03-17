import json
from pathlib import Path

from hippo.models import Cluster, Graph, Node


class GraphStore:
    DEFAULT_GRAPH_PATH = "graph.json"

    def __init__(self, graph_path: str | None = None):
        self._graph_path = (
            Path(graph_path) if graph_path else Path(self.DEFAULT_GRAPH_PATH)
        )
        self._graph: Graph | None = None

    def _require_loaded(self) -> Graph:
        if self._graph is None:
            raise RuntimeError("Graph not loaded. Call load() first.")
        return self._graph

    @property
    def graph(self) -> Graph:
        return self._require_loaded()

    def load(self) -> None:
        if not self._graph_path.exists():
            self._graph = Graph()
            return
        data = json.loads(self._graph_path.read_text())
        self._graph = Graph.from_dict(data)

    def save(self) -> None:
        g = self._require_loaded()
        self._graph_path.parent.mkdir(parents=True, exist_ok=True)
        Path("topics").mkdir(parents=True, exist_ok=True)
        self._graph_path.write_text(json.dumps(g.to_dict(), indent=2))

    def get_node(self, node_id: str) -> Node | None:
        g = self._require_loaded()
        for node in g.topics:
            if node.id == node_id:
                return node
        return None

    def add_node(self, node: Node) -> None:
        g = self._require_loaded()
        g.topics.append(node)

    def remove_node(self, node_id: str) -> None:
        g = self._require_loaded()
        g.topics = [n for n in g.topics if n.id != node_id]
        for node in g.topics:
            if node_id in node.connections:
                del node.connections[node_id]

    def list_nodes(self, cluster: str | None = None) -> list[Node]:
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
