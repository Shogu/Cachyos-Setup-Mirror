from __future__ import annotations

import json
from typing import Callable, Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class JDAPIError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def _json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class JDownloaderAPI:
    """Client for JDownloader's local, unauthenticated Deprecated API.

    The local API represents arguments as JSON values after the question mark,
    e.g. ``/downloadsV2/queryLinks?{...}``. Keeping the encoder here makes the
    GTK layer independent of the slightly unusual wire format.
    """

    DOWNLOAD_QUERY = {
        "addedDate": True,
        "bytesLoaded": True,
        "bytesTotal": True,
        "enabled": True,
        "eta": True,
        "finished": True,
        "host": True,
        "maxResults": -1,
        "name": True,
        "packageUUID": True,
        "packageUUIDs": [],
        "running": True,
        "skipped": True,
        "speed": True,
        "startAt": 0,
        "status": True,
        "uuid": True,
        "url": True,
    }

    GRABBER_QUERY = {
        "availability": True,
        "bytesTotal": True,
        "enabled": True,
        "hosts": True,
        "maxResults": -1,
        "name": True,
        "packageUUIDs": [],
        "startAt": 0,
        "uuid": True,
        "url": True,
        "variantName": True,
    }

    PACKAGE_QUERY = {
        "bytesLoaded": False,
        "bytesTotal": False,
        "childCount": False,
        "enabled": False,
        "finished": False,
        "hosts": False,
        "maxResults": -1,
        "packageUUIDs": [],
        "saveTo": True,
        "startAt": 0,
        "status": False,
    }

    GENERAL_SETTINGS = "org.jdownloader.settings.GeneralSettings"
    GUI_SETTINGS = "org.jdownloader.settings.GraphicalUserInterfaceSettings"

    def __init__(self, base_url: str = "http://127.0.0.1:3128", timeout: float = 6.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def build_url(base_url: str, path: str, params: Iterable[Any] | Any | None = None) -> str:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        if params is None:
            return url
        if isinstance(params, (list, tuple)):
            values = params
        else:
            values = (params,)
        encoded = "&".join(quote(_json_value(value), safe="") for value in values)
        return f"{url}?{encoded}"

    def call(
        self,
        path: str,
        params: Iterable[Any] | Any | None = None,
        method: str = "GET",
        timeout: float | None = None,
    ) -> Any:
        url = self.build_url(self.base_url, path, params)
        request = Request(
            url,
            data=b"" if method.upper() == "POST" else None,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method=method.upper(),
        )
        try:
            with urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            detail = f"API JDownloader ({exc.code})"
            if body:
                detail += f" : {body[:240]}"
            raise JDAPIError(detail, status=exc.code, body=body) from exc
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise JDAPIError(f"API JDownloader inaccessible : {reason}") from exc
        except TimeoutError as exc:
            raise JDAPIError("Délai dépassé lors de la connexion à JDownloader") from exc
        except OSError as exc:
            raise JDAPIError(f"Erreur réseau vers l'API JDownloader : {exc}") from exc

        if not raw:
            return None
        text = raw.decode("utf-8", errors="replace")
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(result, dict) and result.get("type") and result.get("src"):
            error_type = result.get("type")
            raise JDAPIError(f"JDownloader a renvoyé l'erreur {error_type}", body=text)
        return result

    def mutate(self, path: str, params: Iterable[Any] | Any | None = None) -> Any:
        """Use POST first and GET as a compatibility fallback.

        Different JD2 builds accept one or both verbs on the deprecated local
        API. Arguments remain in the URL in both cases, matching its documented
        local format.
        """
        try:
            return self.call(path, params, method="POST")
        except JDAPIError as exc:
            if exc.status not in {400, 404, 405}:
                raise
            return self.call(path, params, method="GET")

    @staticmethod
    def _as_list(result: Any) -> list[dict[str, Any]]:
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        if isinstance(result, dict):
            for key in ("data", "items", "links", "packages"):
                if isinstance(result.get(key), list):
                    return [item for item in result[key] if isinstance(item, dict)]
        return []

    def ping(self) -> bool:
        try:
            self.call("/jd/version", timeout=2.5)
            return True
        except JDAPIError:
            return False

    def version(self) -> Any:
        return self.call("/jd/version")

    def current_state(self) -> str:
        result = self.call("/downloadcontroller/getCurrentState")
        return str(result or "UNKNOWN")

    def query_downloads(self) -> list[dict[str, Any]]:
        return self._as_list(self.call("/downloadsV2/queryLinks", [self.DOWNLOAD_QUERY]))

    def query_download_packages(self) -> list[dict[str, Any]]:
        """Return package destinations used to resolve a link's exact file."""
        return self._as_list(self.call("/downloadsV2/queryPackages", [self.PACKAGE_QUERY]))

    def query_grabber(self) -> list[dict[str, Any]]:
        try:
            result = self.call("/linkgrabberv2/queryLinks", [self.GRABBER_QUERY])
        except JDAPIError as first_error:
            try:
                result = self.call("/linkcollector/queryLinks", [self.GRABBER_QUERY])
            except JDAPIError:
                raise first_error
        return self._as_list(result)

    def add_links(self, links: str, destination_folder: str = "") -> Any:
        payload = {
            "autostart": False,
            "destinationFolder": destination_folder or None,
            "downloadPassword": None,
            "extractPassword": None,
            "links": links,
            "overwritePackagizerRules": False,
            "packageName": None,
            "priority": "DEFAULT",
        }
        try:
            return self.mutate("/linkgrabberv2/addLinks", [payload])
        except JDAPIError:
            # Older local API builds expose the original linkcollector method.
            return self.mutate(
                "/linkcollector/addLinks",
                [links, "", "", "", destination_folder or ""],
            )

    def add_links_batch(
        self,
        urls: Iterable[str],
        destination_folder: str = "",
        on_progress: Callable[[int, int], None] | None = None,
    ) -> tuple[int, list[tuple[str, str]]]:
        """Queue links one call at a time, never aborting the batch on one error.

        One call per URL is what makes JDownloader build one package per page,
        which keeps a whole browser window readable in the Grabber tab. A
        single rejected URL used to abort the loop and drop every address
        after it; now each failure is recorded and the rest still go through.
        """

        sent = 0
        failures: list[tuple[str, str]] = []
        materialisees = list(urls)
        total = len(materialisees)
        for index, url in enumerate(materialisees, start=1):
            try:
                self.add_links(url, destination_folder)
            except Exception as exc:
                failures.append((url, str(exc).strip() or exc.__class__.__name__))
            else:
                sent += 1
            if on_progress is not None:
                # Pages traitees, pas pages reussies : l'attente doit avancer
                # meme quand une adresse est refusee.
                on_progress(index, total)
        return sent, failures

    def move_to_downloads(self, link_ids: list[int], package_ids: list[int]) -> Any:
        return self.mutate("/linkgrabberv2/moveToDownloadlist", [link_ids, package_ids])

    def remove_grabber_links(self, link_ids: list[int], package_ids: list[int]) -> Any:
        return self.mutate("/linkgrabberv2/removeLinks", [link_ids, package_ids])

    def remove_downloads(self, link_ids: list[int], package_ids: list[int]) -> Any:
        try:
            return self.mutate("/downloadsV2/removeLinks", [link_ids, package_ids])
        except JDAPIError as first_error:
            # Older local API builds expose the same action in /downloads.
            try:
                return self.mutate("/downloads/removeLinks", [link_ids, package_ids])
            except JDAPIError:
                raise first_error

    def disable_downloads(self, link_ids: list[int], package_ids: list[int]) -> Any:
        """Disable exactly the selected download links."""
        try:
            # This is the V2 per-link state operation. It is more reliable for
            # an active transfer than the older disableLinks alias.
            return self.set_download_enabled(False, link_ids, package_ids)
        except JDAPIError as first_error:
            try:
                return self.mutate("/downloads/disableLinks", [link_ids, package_ids])
            except JDAPIError:
                raise first_error

    def enable_downloads(self, link_ids: list[int], package_ids: list[int]) -> Any:
        """Enable exactly the selected download links."""
        try:
            return self.set_download_enabled(True, link_ids, package_ids)
        except JDAPIError as first_error:
            try:
                return self.mutate("/downloads/enableLinks", [link_ids, package_ids])
            except JDAPIError:
                raise first_error

    def reset_downloads(self, link_ids: list[int], package_ids: list[int]) -> Any:
        """Reset the state of exactly the selected download links."""
        try:
            return self.mutate("/downloadsV2/resetLinks", [link_ids, package_ids])
        except JDAPIError as first_error:
            try:
                return self.mutate("/downloads/resetLinks", [link_ids, package_ids])
            except JDAPIError:
                raise first_error

    def set_download_enabled(
        self, enabled: bool, link_ids: list[int], package_ids: list[int]
    ) -> Any:
        """Change the enabled state of only the selected links."""
        return self.mutate(
            "/downloadsV2/setEnabled", [bool(enabled), link_ids, package_ids]
        )

    def set_download_directory(self, directory: str, link_ids: list[int]) -> Any:
        """Set an exact destination for the selected download links."""
        return self.mutate("/downloadsV2/setDownloadDirectory", [directory, link_ids])

    def set_config_value(
        self,
        interface_name: str,
        storage: str | None,
        key: str,
        value: Any,
    ) -> Any:
        """Set one native JDownloader advanced-config value."""
        return self.mutate("/config/set", [interface_name, storage, key, value])

    def apply_download_preferences(
        self, max_simultaneous_downloads: int, duplicate_action: str
    ) -> None:
        self.set_max_simultaneous_downloads(max_simultaneous_downloads)
        self.set_config_value(
            self.GENERAL_SETTINGS,
            None,
            "IfFileExistsAction",
            duplicate_action,
        )

    def set_max_simultaneous_downloads(self, value: int) -> Any:
        self.set_config_value(
            self.GENERAL_SETTINGS,
            None,
            "MaxSimultaneDownloads",
            int(value),
        )

    def disable_clipboard_monitoring(self) -> Any:
        """Disable JDownloader's native clipboard observer from old installs."""
        return self.set_config_value(
            self.GUI_SETTINGS,
            None,
            "ClipboardMonitored",
            False,
        )

    def start_downloads(self) -> Any:
        return self.mutate("/downloadcontroller/start")

    def force_downloads(self, link_ids: list[int], package_ids: list[int]) -> Any:
        """Start the selected links immediately, bypassing queue state."""
        try:
            return self.mutate("/downloadcontroller/forceDownload", [link_ids, package_ids])
        except JDAPIError as first_error:
            # Some builds expose the same action in the downloadsV2 namespace.
            try:
                return self.mutate("/downloadsV2/forceDownload", [link_ids, package_ids])
            except JDAPIError:
                raise first_error

    def stop_downloads(self) -> Any:
        return self.mutate("/downloadcontroller/stop")

    def exit_jdownloader(self) -> Any:
        return self.mutate("/system/exitJD")
