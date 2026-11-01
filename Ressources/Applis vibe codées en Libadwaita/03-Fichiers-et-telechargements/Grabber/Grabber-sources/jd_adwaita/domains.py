from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


def normalize_domain(value: Any) -> str:
    """Normalize a domain or a domain pattern entered by the user.

    ``example.com`` and ``*.example.com`` intentionally have the same
    meaning: the exact host and all of its subdomains are accepted.  This is
    easier to explain and safer than interpreting a pattern such as
    ``youtube.*`` as an unrestricted suffix wildcard.
    """

    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw if "://" in raw else f"//{raw}")
        hostname = parsed.hostname
    except ValueError:
        hostname = None
    if hostname:
        raw = hostname
    else:
        raw = raw.split("/", 1)[0].split(":", 1)[0]
    if raw.startswith("*."):
        raw = raw[2:]
    raw = raw.lstrip(".").rstrip(".")
    if not raw:
        return ""
    try:
        return raw.encode("idna").decode("ascii")
    except UnicodeError:
        return raw


def normalize_domain_list(values: Any) -> list[str]:
    if isinstance(values, str):
        values = values.splitlines()
    if not isinstance(values, (list, tuple, set)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        domain = normalize_domain(value)
        if domain and domain not in seen:
            result.append(domain)
            seen.add(domain)
    return result


def domain_matches(host: Any, pattern: Any) -> bool:
    normalized_host = normalize_domain(host)
    normalized_pattern = normalize_domain(pattern)
    if not normalized_host or not normalized_pattern:
        return False
    return normalized_host == normalized_pattern or normalized_host.endswith(
        "." + normalized_pattern
    )
