from __future__ import annotations

from urllib.parse import quote
from urllib.request import Request, urlopen


YOUTUBE_FAVICON_FALLBACK = b"""\
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect x="2" y="10" width="60" height="44" rx="13" fill="#ff0033"/>
  <path d="M27 22.5 47 32 27 41.5Z" fill="#fff"/>
</svg>
"""


def _youtube_service_host(host: str) -> str | None:
    """Return YouTube's canonical host for its short links and CDN hosts."""

    youtube_hosts = (
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        "ytimg.com",
        "googlevideo.com",
    )
    if host in youtube_hosts or any(host.endswith(f".{suffix}") for suffix in youtube_hosts):
        return "youtube.com"
    return None


def fetch_favicon(host: str, timeout: float = 4.0) -> bytes | None:
    """Fetch a small favicon without blocking the GTK main loop."""

    host = host.strip().lower().strip(".")
    if not host or len(host) > 253 or any(char.isspace() for char in host):
        return None

    # JDownloader may expose YouTube's CDN host (or a CDN subdomain) instead
    # of the service host. Use YouTube's own favicon rather than a generic
    # favicon returned for the CDN domain.
    service_host = _youtube_service_host(host) or host
    direct_hosts = [service_host]
    if service_host == "youtube.com":
        direct_hosts.insert(0, "www.youtube.com")

    urls = [
        *(f"https://{candidate}/favicon.ico" for candidate in direct_hosts),
        f"https://www.google.com/s2/favicons?domain={quote(service_host, safe='')}&sz=64",
    ]
    for url in urls:
        request = Request(
            url,
            headers={
                "Accept": "image/avif,image/webp,image/png,image/*;q=0.8,*/*;q=0.5",
                "User-Agent": "grabber/0.10.24",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                content_type = ""
                headers = getattr(response, "headers", None)
                if headers is not None:
                    try:
                        content_type = str(headers.get_content_type() or "")
                    except (AttributeError, TypeError):
                        content_type = str(headers.get("Content-Type") or "")
                if content_type and not content_type.lower().startswith("image/"):
                    continue
                data = response.read(512 * 1024 + 1)
        except (OSError, TimeoutError):
            continue
        if 0 < len(data) <= 512 * 1024:
            return data
    if service_host == "youtube.com":
        # Keep the service recognizable when the user is offline or a CDN
        # blocks favicon requests. Network responses are still preferred.
        return YOUTUBE_FAVICON_FALLBACK
    return None
