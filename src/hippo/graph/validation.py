from dataclasses import dataclass

from hippo.models import Topic, Cluster

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
