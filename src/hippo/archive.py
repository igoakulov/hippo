import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from hippo.directories import get_hippo_dir

ArchiveRefType = Literal["url", "local_file", "x_post", "chat"]


@dataclass
class ArchiveRef:
    type: ArchiveRefType
    value: str
    topics: list[str]
    added_at: str
    removed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "value": self.value,
            "topics": self.topics,
            "added_at": self.added_at,
            "removed_at": self.removed_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ArchiveRef":
        return ArchiveRef(
            type=data["type"],
            value=data["value"],
            topics=data.get("topics", []),
            added_at=data["added_at"],
            removed_at=data.get("removed_at"),
        )


@dataclass
class Archive:
    references: list[ArchiveRef] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"references": [r.to_dict() for r in self.references]}

    @staticmethod
    def from_dict(data: dict) -> "Archive":
        return Archive(
            references=[ArchiveRef.from_dict(r) for r in data.get("references", [])]
        )


def get_archive_path() -> Path:
    return get_hippo_dir() / "archive.json"


def load_archive() -> Archive:
    path = get_archive_path()
    if not path.exists():
        return Archive()
    return Archive.from_dict(json.loads(path.read_text()))


def save_archive(archive: Archive) -> None:
    path = get_archive_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(archive.to_dict(), indent=2))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_reference(ref_type: ArchiveRefType, value: str, topics: list[str]) -> None:
    archive = load_archive()
    existing = None
    for ref in archive.references:
        if ref.type == ref_type and ref.value == value:
            existing = ref
            break

    if existing:
        for topic in topics:
            if topic not in existing.topics:
                existing.topics.append(topic)
    else:
        archive.references.append(
            ArchiveRef(
                type=ref_type,
                value=value,
                topics=topics,
                added_at=now_iso(),
            )
        )

    save_archive(archive)


def remove_reference(
    ref_type: ArchiveRefType, value: str, topics: list[str] | None = None
) -> None:
    archive = load_archive()
    for ref in archive.references:
        if ref.type == ref_type and ref.value == value:
            if topics is None:
                ref.removed_at = now_iso()
            else:
                for topic in topics:
                    if topic in ref.topics:
                        ref.topics.remove(topic)
                if not ref.topics:
                    ref.removed_at = now_iso()
            break

    save_archive(archive)


def sync_archive_from_topics(topics: list[dict]) -> None:
    archive = load_archive()
    current_refs: set[tuple[str, str]] = set()

    for topic in topics:
        for source in topic.get("sources", []):
            ref_type = _infer_source_type(source)
            if ref_type:
                current_refs.add((ref_type, source))
                _upsert_reference(archive, ref_type, source, [topic["id"]])

    for ref in archive.references:
        if (ref.type, ref.value) not in current_refs and ref.removed_at is None:
            ref.removed_at = now_iso()

    save_archive(archive)


def _infer_source_type(value: str) -> ArchiveRefType | None:
    if value.startswith("https://x.com/") or value.startswith("http://x.com/"):
        return "x_post"
    if value.startswith("chats/") or value.endswith(".md"):
        return "chat"
    if value.startswith("sources/x_posts/"):
        return "x_post"
    if value.startswith("~/"):
        return "local_file"
    if value.startswith("/") or ":" in value:
        return "local_file"
    if value.startswith("https://") or value.startswith("http://"):
        return "url"
    return None


def _upsert_reference(
    archive: Archive, ref_type: ArchiveRefType, value: str, topics: list[str]
) -> None:
    for ref in archive.references:
        if ref.type == ref_type and ref.value == value:
            for topic in topics:
                if topic not in ref.topics:
                    ref.topics.append(topic)
            return

    archive.references.append(
        ArchiveRef(
            type=ref_type,
            value=value,
            topics=topics,
            added_at=now_iso(),
        )
    )
