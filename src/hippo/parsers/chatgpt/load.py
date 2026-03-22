import json
from pathlib import Path


def load_conversations(path: Path) -> list[dict]:
    path = path.expanduser().resolve()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_conversations(
    conversations: list[dict],
    from_time: float | None,
    till_time: float | None,
    titles: list[str] | None,
) -> list[dict]:
    titles_lower = [t.lower() for t in titles] if titles else None

    result = []
    for conv in conversations:
        create_time = conv.get("create_time", 0)

        if from_time is not None and create_time < from_time:
            continue
        if till_time is not None and create_time > till_time:
            continue

        if titles_lower:
            title = conv.get("title", "").lower()
            if not any(t in title for t in titles_lower):
                continue

        result.append(conv)

    return result
