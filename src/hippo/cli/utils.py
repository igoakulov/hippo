from dataclasses import dataclass
from datetime import datetime


@dataclass
class SetMetadataResult:
    updated_count: int
    errors: list

    def __init__(self, updated_count: int, errors: list):
        self.updated_count = updated_count
        self.errors = errors


def _group_by_topic(items: list, attr: str) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for item in items:
        topic_id = getattr(item, attr)
        if topic_id not in grouped:
            grouped[topic_id] = []
        grouped[topic_id].append(item)
    return grouped


def _print_errors(errors: list, filename_attr: str = "filename") -> None:
    if not errors:
        return
    grouped = _group_by_topic(errors, "topic_id")
    print("ERRORS")
    for topic_id, items in grouped.items():
        filename = getattr(items[0], filename_attr)
        print(f"{topic_id} ({filename}):")
        for item in items:
            print(f"- {item.message}")


def _print_warnings(warnings: list) -> None:
    if not warnings:
        return
    grouped = _group_by_topic(warnings, "topic_id")
    print("WARNINGS")
    for topic_id, items in grouped.items():
        filename = items[0].filename
        print(f"{topic_id} ({filename}):")
        for item in items:
            print(f"- {item.message}")


def _count_connections(topics: list) -> int:
    count = 0
    for topic in topics:
        if topic.parent:
            count += 1
        count += len(topic.related)
    return count


def _parse_iso_datetime(s: str) -> datetime:
    s = s.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"Cannot parse datetime: {s}")
