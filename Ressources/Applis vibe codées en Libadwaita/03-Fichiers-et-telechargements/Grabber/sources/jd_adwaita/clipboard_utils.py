from __future__ import annotations

import re
from urllib.parse import urlsplit


_HTTP_URL = re.compile(r"https?://[^\s<>\"'`→➜➝➞]+", re.IGNORECASE)
_TRAILING_PUNCTUATION = ".,;:!?)]}→➜➝➞"


def extract_http_urls(text: str) -> list[str]:
    """Return the unique HTTP(S) URLs found in a block of text.

    The text may hold a single pasted URL, a browser tab URL, or several URLs
    separated by spaces, newlines or arrows.  JDownloader's addLinks endpoint
    accepts newline-separated URLs, so every valid candidate is kept.
    """

    result: list[str] = []
    seen: set[str] = set()
    for match in _HTTP_URL.finditer(text or ""):
        candidate = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        if not candidate:
            continue
        try:
            parsed = urlsplit(candidate)
        except ValueError:
            continue
        if not parsed.hostname:
            continue
        if candidate not in seen:
            result.append(candidate)
            seen.add(candidate)
    return result
