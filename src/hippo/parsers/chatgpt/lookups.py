import re

from hippo.parsers.chatgpt.transform import _clean_url


def _build_content_references_lookup(msg: dict) -> dict[str, str]:
    refs: dict[str, str] = {}

    for ref in msg.get("metadata", {}).get("content_references", []):
        matched_text = ref.get("matched_text", "")
        name = ref.get("name", "")
        ref_type = ref.get("type", "")

        if matched_text and name:
            ref_id_match = re.search(r"\ue200filecite\ue202(.+?)\ue201", matched_text)
            if ref_id_match:
                ref_id = ref_id_match.group(1)
                refs[ref_id] = name
            elif ref_type == "file":
                refs[matched_text] = name
            else:
                refs[matched_text] = name

    return refs


def _build_cite_lookups(
    msg: dict,
) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]]]:
    link_title_lookup: dict[str, tuple[str, str]] = {}
    grouped_lookup: dict[str, tuple[str, str]] = {}

    search_groups = msg.get("metadata", {}).get("search_result_groups", [])
    for group in search_groups:
        domain = group.get("domain", "")
        for entry in group.get("entries", []):
            ref_id = entry.get("ref_id", {})
            turn_index = ref_id.get("turn_index", 0)
            ref_index = ref_id.get("ref_index", 0)
            key = f"turn{turn_index}search{ref_index}"

            url = entry.get("url", "")
            title = entry.get("title", "") or entry.get("attribution", "") or domain
            if url:
                url = _clean_url(url)
                if key not in link_title_lookup:
                    link_title_lookup[key] = (url, title)
                if key not in grouped_lookup:
                    grouped_lookup[key] = (url, title)

    content_refs = msg.get("metadata", {}).get("content_references", [])
    for ref in content_refs:
        ref_type = ref.get("type", "")
        if ref_type not in ("grouped_webpages", "link_title"):
            continue

        url = ref.get("url", "")
        title = ref.get("title", "")
        attribution = ""

        if ref_type == "grouped_webpages":
            items = ref.get("items", [])
            for item in items:
                if not url:
                    url = item.get("url", "")
                if not title:
                    title = item.get("title", "")
                if not attribution:
                    attribution = item.get("attribution", "")
                if url or title or attribution:
                    break

        matched_text = ref.get("matched_text", "")

        if ref_type == "link_title":
            cite_match = re.search(
                r"\ue200link_title\ue202.+?\ue202(.+?)\ue201", matched_text
            )
            if cite_match:
                key = cite_match.group(1)
                if key not in link_title_lookup:
                    if url:
                        link_title_lookup[key] = (_clean_url(url), title)
                    else:
                        refs_in_entry = ref.get("refs", [])
                        for r in refs_in_entry:
                            turn = r.get("turn_index", 0)
                            idx = r.get("ref_index", 0)
                            search_key = f"turn{turn}search{idx}"
                            if search_key in link_title_lookup:
                                existing = link_title_lookup[search_key]
                                link_title_lookup[key] = (existing[0], title)
                                break
        else:
            cite_match = re.search(r"\ue200cite\ue202(.+?)\ue201", matched_text)
            if cite_match:
                key = cite_match.group(1)
                display_title = attribution or title
                if key not in grouped_lookup:
                    if url:
                        grouped_lookup[key] = (_clean_url(url), display_title)
                    else:
                        refs_in_entry = ref.get("refs", [])
                        for r in refs_in_entry:
                            turn = r.get("turn_index", 0)
                            idx = r.get("ref_index", 0)
                            search_key = f"turn{turn}search{idx}"
                            if search_key in grouped_lookup:
                                existing = grouped_lookup[search_key]
                                grouped_lookup[key] = (existing[0], display_title)
                                break

    return link_title_lookup, grouped_lookup


def _build_cite_lookup(msg: dict) -> dict[str, tuple[str, str]]:
    link_title_lookup, grouped_lookup = _build_cite_lookups(msg)
    link_title_lookup.update(grouped_lookup)
    return link_title_lookup
