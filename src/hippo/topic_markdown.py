import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import yaml

from hippo.directories import get_topic_path


@dataclass
class Topic:
    id: str
    title: str
    aliases: list[str] = field(default_factory=list)
    progress: str = "new"
    created_at: str = ""
    updated_at: str = ""
    cluster: str = ""
    parent: str = ""
    related: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "aliases": self.aliases,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "cluster": self.cluster,
            "parent": self.parent,
            "related": self.related,
            "sources": self.sources,
        }

    @staticmethod
    def from_dict(data: dict) -> "Topic":
        return Topic(
            id=data.get("id", ""),
            title=data.get("title", ""),
            aliases=data.get("aliases", []),
            progress=data.get("progress", "new"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            cluster=data.get("cluster", ""),
            parent=data.get("parent", ""),
            related=data.get("related", []),
            sources=data.get("sources", []),
        )


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    fm_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = fm_pattern.search(content)

    if match:
        fm_text = match.group(1)
        body = content[match.end() :]
    else:
        fm_text = ""
        body = content

    fm_text = _strip_yaml_comments(fm_text)

    if fm_text.strip():
        try:
            data = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            return {}, body
    else:
        data = {}

    return data, body


def _strip_yaml_comments(text: str) -> str:
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        result.append(line)
    return "\n".join(result)


def get_frontmatter_order() -> list[str]:
    return [
        "id",
        "title",
        "aliases",
        "progress",
        "created_at",
        "updated_at",
        "cluster",
        "parent",
        "related",
        "sources",
    ]


def frontmatter_to_yaml(data: dict) -> str:
    lines = ["---"]
    for key in get_frontmatter_order():
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: []")
        elif value:
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}:")
    lines.append("---")
    return "\n".join(lines)


def topic_to_markdown(topic: Topic) -> str:
    lines = ["---"]
    for key in get_frontmatter_order():
        if key == "id":
            lines.append(f"id: {topic.id}")
            continue
        value = getattr(topic, key, None)
        if value is None or value == "":
            lines.append(f"{key}:")
            continue
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + f"\n# {topic.title}\n\n"


def topic_from_markdown(topic_id: str, content: str) -> Topic:
    data, _ = parse_frontmatter(content)

    if data.get("aliases") is None:
        data["aliases"] = []
    elif isinstance(data["aliases"], str):
        data["aliases"] = [a.strip() for a in data["aliases"].split(",") if a.strip()]

    if data.get("related") is None:
        data["related"] = []
    if data.get("sources") is None:
        data["sources"] = []

    if data.get("cluster") is None:
        data["cluster"] = ""
    if data.get("parent") is None:
        data["parent"] = ""

    if isinstance(data.get("created_at"), date):
        data["created_at"] = data["created_at"].isoformat()
    if isinstance(data.get("updated_at"), date):
        data["updated_at"] = data["updated_at"].isoformat()

    return Topic.from_dict({**data, "id": data.get("id", topic_id)})


def frontmatter_position(content: str) -> int | None:
    match = re.search(r"^---\s*\n", content, re.MULTILINE)
    return match.start() if match else None


def has_frontmatter(content: str) -> bool:
    return bool(re.search(r"^---\s*\n", content))


def body_has_content(body: str) -> bool:
    return bool(body.strip())


def save_topic(topic: Topic) -> None:
    path = get_topic_path(topic.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(topic_to_markdown(topic))


def load_topic(topic_id: str) -> Topic | None:
    path = get_topic_path(topic_id)
    if not path.exists():
        return None
    return topic_from_markdown(topic_id, path.read_text())


def delete_topic_file(topic_id: str) -> None:
    path = get_topic_path(topic_id)
    if path.exists():
        path.unlink()


def update_frontmatter(topic_id: str, updates: dict[str, Any]) -> None:
    path = get_topic_path(topic_id)
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {topic_id}")

    content = path.read_text()
    data, body = parse_frontmatter(content)

    data.update(updates)
    if "updated_at" not in updates:
        data["updated_at"] = str(date.today())

    lines = ["---"]
    for key in get_frontmatter_order():
        value = data.get(key)
        if value is None or value == "":
            lines.append(f"{key}:")
        elif isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")

    new_content = "\n".join(lines) + f"\n{body}"
    path.write_text(new_content)


def get_frontmatter(topic_id: str) -> dict[str, Any] | None:
    path = get_topic_path(topic_id)
    if not path.exists():
        return None
    data, _ = parse_frontmatter(path.read_text())
    return data
