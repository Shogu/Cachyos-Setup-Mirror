from __future__ import annotations

from urllib.parse import unquote, urlsplit

from .clipboard_utils import extract_http_urls

SCHEME = "grabber"
MAX_URLS = 500
MAX_URL_LENGTH = 8192
_URL_KEYS = {"url", "urls"}


def urls_from_arguments(arguments: list[str]) -> list[str]:
    """Extract HTTP(S) URLs from the arguments of a grabber:// invocation.

    ``grabber://add?url=…`` may repeat ``url`` and may carry a newline
    separated ``urls`` value, so a browser extension can hand over a single
    tab or a whole window in one call.  Bare HTTP(S) arguments are accepted
    too, which keeps ``Grabber.AppImage https://…`` usable from a terminal.
    """

    result: list[str] = []
    for argument in arguments:
        text = str(argument or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered.startswith(("http://", "https://")):
            candidates = extract_http_urls(text)
        elif lowered.startswith(f"{SCHEME}:"):
            candidates = _urls_from_uri(text)
        else:
            continue
        for candidate in candidates:
            if len(candidate) > MAX_URL_LENGTH or candidate in result:
                continue
            result.append(candidate)
            if len(result) >= MAX_URLS:
                return result
    return result


def _urls_from_uri(uri: str) -> list[str]:
    try:
        parsed = urlsplit(uri)
    except ValueError:
        return []
    if parsed.scheme.lower() != SCHEME:
        return []

    # Split by hand instead of using parse_qsl: a literal "+" inside a
    # query value must stay a "+" and must not become a space.
    values: list[str] = []
    for chunk in parsed.query.split("&"):
        if not chunk:
            continue
        key, separator, value = chunk.partition("=")
        if separator and unquote(key).strip().lower() in _URL_KEYS:
            values.append(unquote(value))
    if not values:
        # Tolerate grabber://https://example.com/ and grabber://add/https://…
        # urlsplit() reads the inner scheme as the netloc, so work on the raw
        # remainder of the URI instead of the parsed components.
        remainder = uri[len(SCHEME) + 1 :].lstrip("/")
        for prefix in ("add/", "open/"):
            if remainder.lower().startswith(prefix):
                remainder = remainder[len(prefix) :]
        decoded = unquote(remainder)
        if decoded.lower().startswith(("http://", "https://")):
            values.append(decoded)

    urls: list[str] = []
    for value in values:
        for candidate in extract_http_urls(value):
            if candidate not in urls:
                urls.append(candidate)
    return urls
