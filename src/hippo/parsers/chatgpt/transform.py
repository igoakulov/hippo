import re


def _clean_url(url: str) -> str:
    url = re.sub(r"[?&]utm_source=[^&]*", "", url)
    url = url.rstrip(")")
    return url


def _transform_content(content: str, msg: dict) -> str:
    from hippo.parsers.chatgpt.lookups import (
        _build_cite_lookups,
        _build_content_references_lookup,
    )

    refs = _build_content_references_lookup(msg)
    link_title_lookup, grouped_lookup = _build_cite_lookups(msg)

    def replace_genui(match: re.Match) -> str:
        import json

        try:
            inner = json.loads(match.group(1))
            math_content = inner.get("math_block_widget_common_keywords", {}).get(
                "content", ""
            ) or inner.get("content", "")
            if math_content:
                return f"\\({math_content}\\)"
            return match.group(0)
        except (json.JSONDecodeError, KeyError):
            return match.group(0)

    content = re.sub(
        r"\ue200genui\ue202(\{.+?\})\ue201", replace_genui, content, flags=re.DOTALL
    )

    content = re.sub(
        r"\ue200filecite\ue202(.+?)\ue201",
        lambda m: f"[{refs.get(m.group(1), m.group(1))}]",
        content,
    )

    def replace_link_title(m: re.Match) -> str:
        title = m.group(1)
        key = m.group(2)
        result = link_title_lookup.get(key)
        if result:
            url, cite_title = result
            return f"[{cite_title}]({url})"
        return f"[{title}]"

    content = re.sub(
        r"\ue200link_title\ue202(.+?)\ue202(.+?)\ue201",
        replace_link_title,
        content,
    )

    content = re.sub(r"\ue200entity\ue202(.+?)\ue201", lambda m: m.group(1), content)

    def replace_cite(m: re.Match) -> str:
        key = m.group(1)
        result = grouped_lookup.get(key)
        if result:
            url, title = result
            if title:
                return f"[{title}]({url})"
            return url
        return key

    content = re.sub(r"\ue200cite\ue202(.+?)\ue201", replace_cite, content)

    def replace_original_ref(m: re.Match) -> str:
        key = m.group(1)
        result = link_title_lookup.get(key)
        if result:
            url, title = result
            if title:
                return f"[{title}]({url})"
            return url
        return m.group(0)

    content = re.sub(r"\ue202(.+?)\ue201", replace_original_ref, content)

    return content
