import json
from dataclasses import dataclass
from pathlib import Path

from hippo.archive import sync_archive_from_topics
from hippo.clusters import infer_clusters, Cluster
from hippo.directories import (
    get_graph_path,
    VAULT_DIR,
)
from hippo.topic_markdown import (
    Topic,
    topic_from_markdown,
    frontmatter_position,
    body_has_content,
)


@dataclass
class CleanIssue:
    topic_id: str
    issue_type: str
    message: str


@dataclass
class BuildResult:
    topics: list[Topic]
    edges: list[dict]
    clusters: list[Cluster]
    warnings: list[str]
    clean_issues: list[CleanIssue]


def scan_topics_dir() -> list[Path]:
    topics_dir = VAULT_DIR / "topics"
    if not topics_dir.exists():
        return []
    return sorted(topics_dir.glob("*.md"))


def build_graph() -> BuildResult:
    warnings: list[str] = []
    clean_issues: list[CleanIssue] = []
    topics_dict: dict[str, Topic] = {}
    edges: list[dict] = []
    seen_ids: set[str] = set()

    topic_files = scan_topics_dir()
    if not topic_files:
        return BuildResult([], [], [], [], [])

    for path in topic_files:
        topic_id = path.stem
        try:
            content = path.read_text()
            body = content.split("---", 2)[-1] if "---" in content else ""
            topic = topic_from_markdown(topic_id, content)

            if topic.id in seen_ids:
                warnings.append(f"Duplicate topic id: {topic.id}")
            seen_ids.add(topic.id)

            topics_dict[topic.id] = topic

            if frontmatter_position(content) != 0:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        issue_type="frontmatter_position",
                        message=f"Frontmatter not at top of {topic.id}.md",
                    )
                )

            if not body_has_content(body):
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        issue_type="empty_body",
                        message=f"{topic.id} has no content",
                    )
                )

            if not topic.sources:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        issue_type="no_sources",
                        message=f"{topic.id} has no sources",
                    )
                )

            if not topic.parent and topic.id != "AGENTS":
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        issue_type="no_parent",
                        message=f"{topic.id} has no parent (root topic)",
                    )
                )

        except Exception as e:
            warnings.append(f"Error parsing {topic_id}.md: {e}")
            clean_issues.append(
                CleanIssue(
                    topic_id=topic_id,
                    issue_type="invalid_yaml",
                    message=f"Invalid metadata in {topic_id}.md",
                )
            )

    for topic in topics_dict.values():
        if topic.parent and topic.parent in topics_dict:
            edges.append({"source": topic.id, "target": topic.parent, "type": "parent"})
        elif topic.parent:
            clean_issues.append(
                CleanIssue(
                    topic_id=topic.id,
                    issue_type="orphan_parent",
                    message=f"{topic.id} has orphan parent reference: {topic.parent}",
                )
            )

        for related_id in topic.related:
            if related_id in topics_dict:
                edges.append(
                    {"source": topic.id, "target": related_id, "type": "related"}
                )

    topic_list = list(topics_dict.values())
    topic_dicts = [t.to_dict() for t in topic_list]
    cluster_dicts = infer_clusters(topic_dicts)

    return BuildResult(
        topics=topic_list,
        edges=edges,
        clusters=cluster_dicts,
        warnings=warnings,
        clean_issues=clean_issues,
    )


def save_graph(result: BuildResult) -> None:
    graph_path = get_graph_path()
    graph_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "topics": [t.to_dict() for t in result.topics],
        "edges": result.edges,
        "clusters": [c.to_dict() for c in result.clusters],
    }
    graph_path.write_text(json.dumps(data, indent=2))

    sync_archive_from_topics([t.to_dict() for t in result.topics])


def sync() -> BuildResult:
    result = build_graph()
    save_graph(result)
    return result
