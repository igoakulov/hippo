import json
import re
from dataclasses import dataclass
from pathlib import Path

from hippo.archive import sync_archive_from_topics
from hippo.clusters import infer_clusters, merge_clusters, save_clusters, Cluster
from hippo.directories import (
    get_graph_path,
    VAULT_DIR,
)
from hippo.topic_markdown import (
    Topic,
    topic_from_markdown,
    frontmatter_position,
    body_has_content,
    parse_frontmatter,
)

VALID_PROGRESS_VALUES = {"new", "started", "completed"}


@dataclass
class ValidationError:
    topic_id: str
    filename: str
    message: str


@dataclass
class CleanIssue:
    topic_id: str
    filename: str
    issue_type: str
    message: str


@dataclass
class BuildResult:
    topics: list[Topic]
    clusters: list[Cluster]
    validation_errors: list[ValidationError]
    clean_issues: list[CleanIssue]


def _count_words(body: str) -> int:
    return len(body.split())


def scan_topics_dir() -> list[Path]:
    topics_dir = VAULT_DIR / "topics"
    if not topics_dir.exists():
        return []
    return sorted(topics_dir.glob("*.md"))


def build_graph() -> BuildResult:
    validation_errors: list[ValidationError] = []
    clean_issues: list[CleanIssue] = []
    topics_dict: dict[str, Topic] = {}
    seen_ids: set[str] = set()
    filename_map: dict[str, str] = {}

    topic_files = scan_topics_dir()
    if not topic_files:
        return BuildResult([], [], [], [])

    for path in topic_files:
        topic_id = path.stem
        filename = path.name

        try:
            content = path.read_text()
            data, body = parse_frontmatter(content)

            has_fm = bool(re.search(r"^---\s*\n", content, re.MULTILINE))

            if has_fm and not data:
                validation_errors.append(
                    ValidationError(
                        topic_id=topic_id,
                        filename=filename,
                        message="Metadata frontmatter cannot be parsed",
                    )
                )

            if "id" not in data:
                validation_errors.append(
                    ValidationError(
                        topic_id=topic_id,
                        filename=filename,
                        message="Missing required field: id",
                    )
                )

            topic = topic_from_markdown(topic_id, content)

            filename_map[topic.id] = filename

            if topic.id in seen_ids:
                validation_errors.append(
                    ValidationError(
                        topic_id=topic.id,
                        filename=filename,
                        message="Duplicate topic ID",
                    )
                )
            seen_ids.add(topic.id)

            topics_dict[topic.id] = topic

            if frontmatter_position(content) != 0:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="frontmatter_position",
                        message="Metadata frontmatter not at top of file",
                    )
                )

            if not body_has_content(body):
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="empty_body",
                        message="No content (empty body)",
                    )
                )

            if not topic.sources:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="no_sources",
                        message="No sources in metadata",
                    )
                )

            if not topic.parent and topic.id != "AGENTS":
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="no_parent",
                        message="No parent in metadata (root topic)",
                    )
                )

            if topic.progress and topic.progress not in VALID_PROGRESS_VALUES:
                clean_issues.append(
                    CleanIssue(
                        topic_id=topic.id,
                        filename=filename,
                        issue_type="unknown_progress",
                        message=f"Unknown progress value '{topic.progress}' in metadata",
                    )
                )

        except Exception:
            validation_errors.append(
                ValidationError(
                    topic_id=topic_id,
                    filename=filename,
                    message="Metadata frontmatter cannot be parsed",
                )
            )
            clean_issues.append(
                CleanIssue(
                    topic_id=topic_id,
                    filename=filename,
                    issue_type="invalid_yaml",
                    message="Metadata frontmatter has issues but was parsed",
                )
            )

    for topic in topics_dict.values():
        if topic.parent and topic.parent not in topics_dict:
            clean_issues.append(
                CleanIssue(
                    topic_id=topic.id,
                    filename=filename_map.get(topic.id, f"{topic.id}.md"),
                    issue_type="orphan_parent",
                    message=f"Parent '{topic.parent}' in metadata does not exist",
                )
            )

    topic_list = list(topics_dict.values())
    topic_dicts = [t.to_dict() for t in topic_list]
    inferred = infer_clusters(topic_dicts)
    cluster_dicts = merge_clusters(inferred)

    return BuildResult(
        topics=topic_list,
        clusters=cluster_dicts,
        validation_errors=validation_errors,
        clean_issues=clean_issues,
    )


def _compute_word_counts(topics: list[Topic]) -> dict[str, int]:
    result = {}
    for path in scan_topics_dir():
        topic_id = path.stem
        content = path.read_text()
        _, body = parse_frontmatter(content)
        result[topic_id] = _count_words(body)
    return result


def save_graph(result: BuildResult) -> dict[str, int]:
    from hippo.diffs import compute_diff, save_diff

    graph_path = get_graph_path()
    graph_path.parent.mkdir(parents=True, exist_ok=True)

    old_graph: dict | None = None
    old_word_counts: dict[str, int] = {}
    if graph_path.exists():
        try:
            loaded: dict = json.loads(graph_path.read_text())
            old_graph = loaded
            old_word_counts = loaded.get("word_counts", {}) or {}
        except (json.JSONDecodeError, IOError):
            pass

    word_counts = _compute_word_counts(result.topics)

    data = {
        "topics": [t.to_dict() for t in result.topics],
        "clusters": [c.to_dict() for c in result.clusters],
        "word_counts": word_counts,
    }

    diff = compute_diff(old_graph, data, old_word_counts)
    if not diff.is_empty():
        save_diff(diff)

    save_clusters(result.clusters)
    graph_path.write_text(json.dumps(data, indent=2))

    sync_archive_from_topics([t.to_dict() for t in result.topics])
    return word_counts


def sync() -> BuildResult:
    result = build_graph()
    save_graph(result)
    return result
