from __future__ import annotations

import ctypes
import errno
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

from . import __version__ as APP_VERSION
from . import ytdlp
from .api import JDAPIError, JDownloaderAPI
from .clipboard import ClipboardMonitor
from .clipboard_utils import extract_http_urls
from .config import LOCAL_API_URL, AppConfig
from .domains import domain_matches, normalize_domain_list
from .formatting import (
    as_number,
    estimate_eta_seconds,
    file_category,
    format_bytes,
    format_duration_seconds,
    format_speed,
    progress_for,
    progress_percent,
    source_host_name,
    status_text,
    host_name,
)
from .favicons import fetch_favicon
from .process import JDownloaderProcess
from .settings import (
    open_settings as open_settings_dialog,
    request_jdownloader_update as request_jdownloader_update_dialog,
)
from .ui import build_window, icon_button, install_css, trash_button
from .uri import urls_from_arguments

DELIVERY_RETRY_MS = 250
MAX_REPORTED_FAILURES = 8


class MainWindow(Adw.ApplicationWindow):
    GRABBER_FILTERS = (
        ("Tous les fichiers", "all"),
        ("Musique", "music"),
        ("Vidéos", "videos"),
        ("Documents", "documents"),
    )
    SIMULTANEOUS_DOWNLOAD_OPTIONS = (1, 2, 3, 4, 5, 8, 10, 15, 20)

    def __init__(self, application: Adw.Application, config: AppConfig) -> None:
        super().__init__(application=application, title="Grabber")
        self.set_default_size(900, 680)
        self.set_size_request(620, 480)

        self.config = config
        self.api = JDownloaderAPI(LOCAL_API_URL)
        self.backend = JDownloaderProcess(config)
        self._operation_busy = False
        self._refresh_busy = False
        self._known_online = False
        self._closing = False
        self._shutdown_complete = False
        self._startup_queue_started = False
        self._grabber_rows: list[tuple[Adw.ActionRow, Gtk.CheckButton, Any]] = []
        self._grabber_items: list[dict[str, Any]] = []
        self._selected_grabber_ids: set[int] = set()
        self._grabber_filter = config.grabber_filter
        self._download_package_dirs: dict[str, Path] = {}
        self._download_items: list[dict[str, Any]] = []
        self._selected_download_ids: set[int] = set()
        self._download_eta_samples: dict[int, list[tuple[float, int]]] = {}
        self._native_clipboard_disabled = False
        self._download_context_popover: Gtk.PopoverMenu | None = None
        self._grabber_context_popover: Gtk.PopoverMenu | None = None
        self._pending_download_refresh: tuple[
            list[dict[str, Any]], list[dict[str, Any]]
        ] | None = None
        self._favicon_data: dict[str, bytes | None] = {}
        self._favicon_textures: dict[str, Any] = {}
        self._favicon_loading: set[str] = set()
        self._favicon_images: dict[str, list[Gtk.Picture]] = {}
        self._pending_delivery: str | None = None
        self._delivery_retry_source: int | None = None
        self._clipboard_monitor = ClipboardMonitor(self._on_clipboard_text)
        self._clipboard_scan_source: int | None = None
        self._last_clipboard_text = ""
        self._clipboard_inserted_text = ""
        self._setting_clipboard_entry = False
        self._syncing_grabber_options = False
        raw_moved_paths = config.data.get("moved_video_paths", {})
        self._download_file_overrides: dict[int, Path] = {}
        if isinstance(raw_moved_paths, dict):
            for raw_id, raw_path in raw_moved_paths.items():
                try:
                    self._download_file_overrides[int(raw_id)] = Path(str(raw_path)).expanduser()
                except (TypeError, ValueError):
                    continue

        build_window(self)
        self._sync_grabber_option_switches()
        if self.config.clipboard_scan_enabled:
            self._clipboard_monitor.start()
        GLib.idle_add(self._connect_on_start)
        GLib.timeout_add(2500, self._poll)

    def _connect_on_start(self) -> bool:
        # Grabber has one mode: start and own the embedded JDownloader, then
        # resume the queue that was already present when the app was closed.
        self._start_engine(start_downloads=True)
        return GLib.SOURCE_REMOVE

    def _poll(self) -> bool:
        self._refresh_now()
        return GLib.SOURCE_CONTINUE

    def _refresh_now(self) -> None:
        if self._refresh_busy or self._operation_busy:
            return
        self._refresh_busy = True

        def work() -> dict[str, Any]:
            if not self.api.ping():
                return {"online": False}
            downloads = self.api.query_downloads()
            try:
                packages = self.api.query_download_packages()
            except JDAPIError:
                # Older builds may not expose package queries. The configured
                # download directory remains a usable fallback in that case.
                packages = []
            return {
                "online": True,
                "state": self.api.current_state(),
                "downloads": downloads,
                "packages": packages,
                "grabber": self.api.query_grabber(),
            }

        def success(result: dict[str, Any]) -> None:
            self._refresh_busy = False
            if not result.get("online"):
                self._set_offline()
                return
            self._set_online(str(result.get("state") or "Prêt"))
            self._populate_downloads(
                result.get("downloads", []), result.get("packages", [])
            )
            self._populate_grabber(result.get("grabber", []))

        def error(_exc: Exception) -> None:
            self._refresh_busy = False
            self._set_offline()

        self._run_thread(work, success, error, manage_busy=False)

    def _run_thread(
        self,
        work: Callable[[], Any],
        success: Callable[[Any], None] | None = None,
        error: Callable[[Exception], None] | None = None,
        manage_busy: bool = True,
    ) -> None:
        if manage_busy:
            self._operation_busy = True
            self._set_controls_sensitive(False)

        def runner() -> None:
            try:
                result = work()
            except Exception as exc:  # the GTK callback must run on the main loop
                GLib.idle_add(self._finish_thread, error, exc, manage_busy)
            else:
                GLib.idle_add(self._finish_thread, success, result, manage_busy)

        threading.Thread(target=runner, name="grabber-worker", daemon=True).start()

    def _finish_thread(
        self,
        callback: Callable[[Any], None] | None,
        value: Any,
        manage_busy: bool,
    ) -> bool:
        if manage_busy:
            self._operation_busy = False
            self._set_controls_sensitive(True)
        if callback is not None:
            callback(value)
        return GLib.SOURCE_REMOVE

    def _ensure_backend(self) -> None:
        self.backend.start_and_wait(self.api)
        self._disable_native_clipboard_monitoring()

    def _disable_native_clipboard_monitoring(self) -> None:
        """Disable an old JDownloader clipboard observer left by earlier builds."""

        if self._native_clipboard_disabled:
            return
        try:
            self.api.disable_clipboard_monitoring()
        except JDAPIError:
            return
        self._native_clipboard_disabled = True

    def _start_engine(
        self, *_args: Any, start_downloads: bool = False
    ) -> None:
        self._set_starting()

        def work() -> None:
            self._ensure_backend()
            if start_downloads and not self._startup_queue_started:
                self.api.start_downloads()
                self._startup_queue_started = True

        self._run_thread(work, lambda _result: self._refresh_now(), self._show_error)

    def _start_downloads(self, *_args: Any) -> None:
        self._set_download_controller_state(True)

        def work() -> Any:
            self._ensure_backend()
            return self.api.start_downloads()

        self._run_thread(work, lambda _result: self._refresh_now(), self._show_error)

    def _stop_downloads(self, *_args: Any) -> None:
        self._set_download_controller_state(False)

        def work() -> Any:
            self._ensure_backend()
            return self.api.stop_downloads()

        self._run_thread(work, lambda _result: self._refresh_now(), self._show_error)

    def _on_grabber_entry_changed(self, *_args: Any) -> None:
        if not self._setting_clipboard_entry:
            self._clipboard_inserted_text = ""

    def _sync_grabber_option_switches(self) -> None:
        """Keep the compact Grabber controls aligned with the settings."""

        self._syncing_grabber_options = True
        try:
            clipboard_switch = getattr(self, "grabber_clipboard_switch", None)
            if clipboard_switch is not None:
                clipboard_switch.set_active(self.config.clipboard_scan_enabled)

            whitelist_switch = getattr(self, "grabber_whitelist_switch", None)
            if whitelist_switch is not None:
                whitelist_switch.set_active(self.config.grabber_whitelist_enabled)

            domains_button = getattr(self, "grabber_domains_button", None)
            if domains_button is not None:
                domains_button.set_visible(self.config.grabber_whitelist_enabled)
        finally:
            self._syncing_grabber_options = False

    def _save_grabber_options(self) -> bool:
        try:
            self.config.save()
        except OSError as exc:
            self._show_error(exc)
            return False
        return True

    def deliver_urls(self, urls: list[str], *, focus: bool = False) -> None:
        """Hand URLs received from the grabber:// handler to the scanner.

        The URLs are queued instead of scanned straight away: a delivery can
        arrive while the embedded JDownloader is still starting, and starting a
        second scan thread at that moment would race the engine startup.
        """

        if self._closing or not urls:
            return
        text = "\n".join(urls)
        self._pending_delivery = (
            f"{self._pending_delivery}\n{text}" if self._pending_delivery else text
        )
        self._setting_clipboard_entry = True
        try:
            self.grabber_url_entry.set_text(self._pending_delivery)
            self.grabber_url_entry.set_position(-1)
        finally:
            self._setting_clipboard_entry = False
        # Treat the delivered batch as machine-inserted so a later clipboard
        # copy may still replace it instead of being blocked as user input.
        self._clipboard_inserted_text = self._pending_delivery
        self.stack.set_visible_child_name("grabber")
        if focus:
            self.present()
        self._schedule_delivery_flush()

    def _schedule_delivery_flush(self) -> None:
        if self._delivery_retry_source is not None:
            return
        self._delivery_retry_source = GLib.timeout_add(
            DELIVERY_RETRY_MS, self._flush_pending_delivery
        )

    def _flush_pending_delivery(self) -> bool:
        if self._closing or self._pending_delivery is None:
            self._delivery_retry_source = None
            return GLib.SOURCE_REMOVE
        if self._operation_busy:
            return GLib.SOURCE_CONTINUE
        text, self._pending_delivery = self._pending_delivery, None
        self._delivery_retry_source = None
        self._scan_url_text(text, automatic=True, per_url=True)
        return GLib.SOURCE_REMOVE

    def _on_clipboard_switch_changed(
        self, switch: Gtk.Switch, *_args: Any
    ) -> None:
        if self._syncing_grabber_options:
            return
        self.config.clipboard_scan_enabled = switch.get_active()
        if not self._save_grabber_options():
            self._sync_grabber_option_switches()
            return
        if self.config.clipboard_scan_enabled:
            self._clipboard_monitor.start()
        else:
            self._clipboard_monitor.stop()

    def _on_whitelist_switch_changed(
        self, switch: Gtk.Switch, *_args: Any
    ) -> None:
        if self._syncing_grabber_options:
            return
        self.config.grabber_whitelist_enabled = switch.get_active()
        if not self._save_grabber_options():
            self._sync_grabber_option_switches()
            return
        self._sync_grabber_option_switches()
        self._populate_grabber(self._grabber_items)

    def _scan_grabber_url(self, *_args: Any) -> None:
        self._scan_url_text(self.grabber_url_entry.get_text().strip(), automatic=False)

    def _scan_url_text(
        self, url: str, *, automatic: bool, per_url: bool = False
    ) -> None:
        # Gtk.Entry is single-line, so a multi-URL paste may arrive separated
        # by spaces instead of newlines. Extract every HTTP(S) URL and pass
        # JDownloader the newline-separated batch its addLinks API expects.
        raw_text = (url or "").strip()
        urls = extract_http_urls(raw_text)
        if urls:
            url = "\n".join(urls)
        else:
            url = raw_text
        if not url:
            self._show_error(JDAPIError("Saisis une ou plusieurs URL à scanner."))
            return
        self._begin_scan_feedback()
        scan_button = getattr(self, "grabber_scan_button", None)
        if scan_button is not None:
            scan_button.set_sensitive(False)

        def work() -> Any:
            self._ensure_backend()
            if per_url and urls:
                # One addLinks call per page: JDownloader then builds one
                # package per tab and the Grabber stays readable when a whole
                # window is sent from the browser.
                sent, failures = self.api.add_links_batch(
                    urls, self.config.download_dir
                )
                return {"total": len(urls), "sent": sent, "failures": failures}
            self.api.add_links(url, self.config.download_dir)
            return {"total": 1, "sent": 1, "failures": []}

        def finish_scan() -> None:
            self._end_scan_feedback()
            if scan_button is not None:
                scan_button.set_sensitive(True)

        def done(result: Any) -> None:
            finish_scan()
            if isinstance(result, dict):
                self._toast_scan_outcome(result)
            if not automatic:
                self._clipboard_inserted_text = ""
                self.grabber_url_entry.set_text("")
            if isinstance(result, dict) and result.get("failures"):
                self._report_scan_outcome(result)
            self._refresh_now()

        def failed(exc: Exception) -> None:
            finish_scan()
            self._show_error(exc)

        self._run_thread(work, done, failed)

    def _begin_scan_feedback(self) -> None:
        """Attente visible aux deux endroits canoniques de GNOME : le spinner
        de la barre d'en-tête et le bouton déclencheur, qui devient spinner."""
        spinner = getattr(self, "scan_spinner", None)
        if spinner is not None:
            start = getattr(spinner, "start", None)  # Gtk.Spinner (Adw < 1.6)
            if start is not None:
                start()
            spinner.set_visible(True)
        self._set_scan_button_busy(True)

    def _end_scan_feedback(self) -> None:
        spinner = getattr(self, "scan_spinner", None)
        if spinner is not None:
            stop = getattr(spinner, "stop", None)
            if stop is not None:
                stop()
            spinner.set_visible(False)
        self._set_scan_button_busy(False)

    def _set_scan_button_busy(self, busy: bool) -> None:
        """Échanger l'icône du bouton de scan contre un spinner pendant l'analyse."""
        button = getattr(self, "grabber_scan_button", None)
        icon = getattr(self, "scan_button_icon", None)
        if button is None or icon is None:
            return
        if busy:
            spinner = Adw.Spinner() if hasattr(Adw, "Spinner") else Gtk.Spinner()
            if hasattr(spinner, "start"):
                spinner.start()
            button.set_child(spinner)
        elif button.get_child() is not icon:
            button.set_child(icon)

    def _toast_scan_outcome(self, outcome: dict[str, Any]) -> None:
        """Dire ce que l'analyse a produit : un succes etait jusqu'ici silencieux."""
        overlay = getattr(self, "toast_overlay", None)
        if overlay is None:
            return
        sent = int(outcome.get("sent") or 0)
        failures = len(outcome.get("failures") or [])
        if failures and sent:
            message = f"{sent} lien(s) ajouté(s) au Grabber, {failures} en échec"
        elif failures:
            message = f"Aucun lien ajouté : {failures} adresse(s) en échec"
        else:
            message = f"{sent} lien(s) ajouté(s) au Grabber"
        overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def _report_scan_outcome(self, outcome: dict[str, Any]) -> None:
        """Report a partially failed batch instead of letting it vanish.

        The failed addresses are put back in the entry so a single click
        retries exactly the ones that did not reach JDownloader.
        """

        failures: list[tuple[str, str]] = list(outcome.get("failures") or [])
        self.grabber_url_entry.set_text("\n".join(url for url, _reason in failures))
        self.grabber_url_entry.set_position(-1)
        preview = "\n".join(
            f"• {self._shorten(url)} — {reason}"
            for url, reason in failures[:MAX_REPORTED_FAILURES]
        )
        hidden = len(failures) - MAX_REPORTED_FAILURES
        if hidden > 0:
            preview += f"\n… et {hidden} autre(s) non détaillée(s)."
        sent = int(outcome.get("sent", 0))
        total = int(outcome.get("total", 0))
        body = (
            f"{sent} URL sur {total} transmise(s) à JDownloader.\n"
            f"{len(failures)} en échec, remises dans le champ pour réessayer.\n\n"
            f"{preview}"
        )
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Envoi partiel" if sent else "Aucune URL envoyée",
            body=body,
        )
        dialog.add_response("close", "Fermer")
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.present()

    @staticmethod
    def _shorten(url: str, width: int = 72) -> str:
        return url if len(url) <= width else f"{url[: width - 1]}…"

    def _on_clipboard_text(self, text: str) -> None:
        """Fill the Grabber and scan a newly copied HTTP(S) URL."""

        if self._closing or not self.config.clipboard_scan_enabled:
            return
        urls = extract_http_urls(text)
        if not urls:
            return
        clipboard_text = "\n".join(urls)
        current = self.grabber_url_entry.get_text().strip()
        if current and current != self._clipboard_inserted_text:
            # Do not overwrite a URL the user is actively editing.
            return
        if clipboard_text == self._last_clipboard_text:
            return
        self._last_clipboard_text = clipboard_text

        self._setting_clipboard_entry = True
        try:
            self.grabber_url_entry.set_text(clipboard_text)
            self.grabber_url_entry.set_position(-1)
        finally:
            self._setting_clipboard_entry = False
        self._clipboard_inserted_text = clipboard_text
        self.stack.set_visible_child_name("grabber")

        if self._clipboard_scan_source is not None:
            GLib.source_remove(self._clipboard_scan_source)
        self._clipboard_scan_source = GLib.timeout_add(
            300, self._scan_clipboard_text, clipboard_text
        )

    def _scan_clipboard_text(self, text: str) -> bool:
        self._clipboard_scan_source = None
        if self._closing or not self.config.clipboard_scan_enabled:
            return GLib.SOURCE_REMOVE
        if self.grabber_url_entry.get_text().strip() != text:
            return GLib.SOURCE_REMOVE
        self._scan_url_text(text, automatic=True)
        return GLib.SOURCE_REMOVE

    def _select_all_grabber(self, *_args: Any) -> None:
        """Select every visible Grabber link, respecting the active filter."""

        for _row, check, link_id in self._grabber_rows:
            if link_id is not None and not check.get_active():
                check.set_active(True)

    def _confirm_grabber(self, *_args: Any) -> None:
        link_ids: list[int] = []
        for _row, check, link_id in self._grabber_rows:
            if not check.get_active():
                continue
            if link_id is not None:
                link_ids.append(int(link_id))
        if not link_ids:
            self._show_error(JDAPIError("Sélectionne au moins un lien."))
            return

        selected = {
            int(item["uuid"]): item
            for item in self._grabber_items
            if item.get("uuid") is not None
        }

        duplicate_names = self._find_duplicate_grabber_names(link_ids, selected)
        if duplicate_names:
            self._ask_duplicate_action(link_ids, duplicate_names)
            return
        self._queue_selected_grabber(link_ids, "AUTO_RENAME")

    def _find_duplicate_grabber_names(
        self, link_ids: list[int], selected: dict[int, dict[str, Any]]
    ) -> list[str]:
        """Find names already queued or present in the destination folder.

        JDownloader may choose an automatic renamed filename only after a link
        enters the download list. Checking both the current queue and the
        filesystem lets the frontend ask before that move, including when the
        existing entry is still represented by a ``.part`` file.
        """
        root = Path(self.config.download_dir).expanduser()
        selected_names: dict[str, int] = {}
        for link_id in link_ids:
            item = selected.get(link_id)
            raw_name = str((item or {}).get("name") or "").strip()
            name = Path(raw_name).name if raw_name else ""
            if name:
                selected_names[name] = selected_names.get(name, 0) + 1

        queued_names: set[str] = set()
        for item in self._download_items:
            raw_name = str(item.get("name") or "").strip()
            if raw_name:
                queued_names.add(Path(raw_name).name)
        duplicate_names: set[str] = {
            name for name, count in selected_names.items() if count > 1
        }

        for name in selected_names:
            if name in queued_names:
                duplicate_names.add(name)
                continue
            exact_candidates = (root / name, root / f"{name}.part")
            if any(candidate.is_file() for candidate in exact_candidates):
                duplicate_names.add(name)
                continue
            try:
                matches = [
                    path
                    for candidate_name in (name, f"{name}.part")
                    for path in root.rglob(candidate_name)
                    if path.is_file()
                ]
            except OSError:
                matches = []
            if matches:
                duplicate_names.add(name)

        return sorted(duplicate_names, key=str.casefold)

    def _ask_duplicate_action(
        self,
        link_ids: list[int],
        duplicate_names: list[str],
    ) -> None:
        visible_names = duplicate_names[:5]
        listed = "\n".join(f"• {name}" for name in visible_names)
        if len(duplicate_names) > len(visible_names):
            listed += f"\n• … et {len(duplicate_names) - len(visible_names)} autre(s)"
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Doublon détecté",
            body=(
                "Un fichier portant déjà ce nom est dans la file ou dans le dossier "
                "de destination :\n\n"
                f"{listed}\n\n"
                "Choisis ce que JDownloader doit faire pour la sélection."
            ),
        )
        dialog.add_response("rename", "Renommer")
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("replace", "Remplacer")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_response_appearance("replace", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("rename")
        dialog.set_close_response("cancel")

        def on_response(_dialog: Adw.MessageDialog, response: str) -> None:
            if response == "rename":
                self._queue_selected_grabber(link_ids, "AUTO_RENAME")
            elif response == "replace":
                self._queue_selected_grabber(link_ids, "OVERWRITE_FILE")

        dialog.connect("response", on_response)
        dialog.present()

    def _queue_selected_grabber(
        self,
        link_ids: list[int],
        duplicate_action: str,
    ) -> None:
        def work() -> Any:
            self._ensure_backend()
            self.api.apply_download_preferences(
                self.config.max_simultaneous_downloads,
                duplicate_action,
            )
            self.api.move_to_downloads(link_ids, [])
            try:
                return self.api.force_downloads(link_ids, [])
            except JDAPIError:
                # Keep compatibility with older JDownloader builds that do
                # not expose forceDownload in their local API.
                return self.api.start_downloads()

        def done(_result: Any) -> None:
            self._selected_grabber_ids.difference_update(link_ids)
            self.stack.set_visible_child_name("downloads")
            self._refresh_now()

        self._run_thread(work, done, self._show_error)

    def _apply_download_preferences(self) -> None:
        self._ensure_backend()
        self.api.set_max_simultaneous_downloads(self.config.max_simultaneous_downloads)

    def _ask_reset_download(self, item: dict[str, Any]) -> None:
        path = self._download_file_path(item)
        if path is None:
            self._show_error(JDAPIError("Le chemin du fichier téléchargé est inconnu."))
            return

        name = str(item.get("name") or path.name)
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Réinitialiser le téléchargement ?",
            body=(
                f"Supprimer « {name} » et ses données partielles, puis recommencer "
                "le téléchargement depuis zéro ?"
            ),
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("reset", "Réinitialiser")
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(_dialog: Adw.MessageDialog, response: str) -> None:
            if response == "reset":
                self._reset_download(item, path)

        dialog.connect("response", on_response)
        dialog.present()

    def _reset_download(self, item: dict[str, Any], path: Path) -> None:
        link_id = item.get("uuid")
        if link_id is None:
            return
        link_ids = [int(link_id)]

        def work() -> dict[str, Any]:
            self._ensure_backend()

            # Disable this exact link first. This prevents JDownloader from
            # recreating a .part file while its old artifacts are removed.
            try:
                self.api.disable_downloads(link_ids, [])
            except JDAPIError as exc:
                raise JDAPIError(
                    "Impossible d’arrêter ce lien avant sa réinitialisation : "
                    f"{exc}"
                ) from exc

            # The final rename can happen between opening the dialog and this
            # worker. Resolve the current exact path again before unlinking.
            refreshed = self._download_file_path(item)
            target = refreshed if refreshed is not None else path
            deleted = False
            local_error: str | None = None
            for artifact in self._download_artifact_paths(target, item):
                try:
                    artifact.unlink()
                    deleted = True
                except FileNotFoundError:
                    continue
                except IsADirectoryError as exc:
                    local_error = f"Le chemin attendu est un fichier : {artifact} ({exc})"
                    break
                except OSError as exc:
                    local_error = f"{artifact} ({exc})"
                    break
            if local_error:
                raise JDAPIError(
                    "Impossible de supprimer complètement l’ancien fichier avant "
                    f"la réinitialisation : {local_error}"
                )

            # resetLinks clears JDownloader's state, while forceDownload starts
            # only this link again. Re-enable it because it was disabled above.
            self.api.reset_downloads(link_ids, [])
            self.api.enable_downloads(link_ids, [])
            self.api.force_downloads(link_ids, [])
            return {"deleted": deleted}

        def done(result: dict[str, Any]) -> None:
            if result["deleted"]:
                self.engine_hint.set_text(
                    "Téléchargement réinitialisé et relancé depuis zéro"
                )
            else:
                self.engine_hint.set_text(
                    "Téléchargement réinitialisé et relancé (ancien fichier absent)"
                )
            self._refresh_now()

        self._run_thread(work, done, self._show_error)

    def _attach_download_context_menu(
        self, row: Adw.ActionRow, item: dict[str, Any]
    ) -> None:
        """Add persistent, visible per-download actions and a native menu."""
        actions = Gio.SimpleActionGroup()
        link_id = item.get("uuid")
        has_link_id = link_id is not None
        menu = Gio.Menu()

        reset_action = Gio.SimpleAction.new("reset", None)
        reset_action.set_enabled(has_link_id)
        reset_action.connect("activate", lambda *_args, download=item: self._ask_reset_download(download))
        actions.add_action(reset_action)
        menu.append("Réinitialiser le téléchargement", "download.reset")
        ytdlp_action = Gio.SimpleAction.new("ytdlp", None)
        ytdlp_action.set_enabled(bool(item.get("url")))
        ytdlp_action.connect("activate", lambda *_args, download=item: self._download_with_ytdlp(download))
        actions.add_action(ytdlp_action)
        menu.append("Télécharger avec yt-dlp (cookies du navigateur)", "download.ytdlp")

        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", lambda *_args, download=item: self._ask_delete_download_file(download))
        actions.add_action(delete_action)
        menu.append("Supprimer le fichier et le téléchargement…", "download.delete")

        row.insert_action_group("download", actions)
        file_path = self._download_file_path(item)
        open_file = icon_button("document-open-symbolic")
        open_file.add_css_class("flat")
        open_file.set_tooltip_text("Ouvrir le fichier")
        open_file.set_sensitive(file_path is not None and file_path.is_file())
        open_file.connect("clicked", lambda *_args, download=item: self._open_download_file(download))
        row.add_suffix(open_file)

        open_folder = icon_button("folder-symbolic")
        open_folder.add_css_class("flat")
        open_folder.set_tooltip_text("Ouvrir le dossier contenant le fichier")
        open_folder.set_sensitive(file_path is not None)
        open_folder.connect("clicked", lambda *_args, download=item: self._open_download_folder(download))
        row.add_suffix(open_folder)

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.add_css_class("flat")
        menu_button.add_css_class("circular")
        menu_button.add_css_class("icon-action")
        menu_button.set_size_request(28, 28)
        menu_button.set_halign(Gtk.Align.CENTER)
        menu_button.set_valign(Gtk.Align.CENTER)
        menu_button.set_hexpand(False)
        menu_button.set_vexpand(False)
        menu_button.set_tooltip_text("Autres actions : réinitialiser ou supprimer")
        menu_button.set_menu_model(menu)
        row.add_suffix(menu_button)

    def _link_url(self, item: dict[str, Any]) -> str:
        """Pick the original link out of JDownloader's several URL-ish fields."""
        for key in ("url", "sourceUrl", "source_url", "originUrl", "origin_url"):
            value = item.get(key)
            if isinstance(value, (list, tuple)):
                value = value[0] if value else None
            text = str(value or "").strip()
            if text.startswith(("http://", "https://")):
                return text
        return ""

    def _download_with_ytdlp(self, item: dict[str, Any]) -> None:
        """Hand a single link to the bundled yt-dlp, cookies included."""
        url = self._link_url(item)
        if not url:
            ytdlp.write_note(
                f"aucune URL exploitable pour {item.get('name')!r}; champs recus : {sorted(item)}"
            )
            self._show_error(
                RuntimeError(
                    "Ce téléchargement ne contient pas d’URL exploitable. "
                    f"Le détail des champs reçus est dans {ytdlp.default_log_path()}"
                )
            )
            return
        target = self._download_file_path(item)
        directory = target.parent if target is not None else Path(self.config.download_dir).expanduser()
        self.engine_hint.set_text(f"yt-dlp : {url}")

        def work() -> tuple[bool, str]:
            return ytdlp.download(
                url,
                directory,
                on_line=lambda line: GLib.idle_add(
                    self.engine_hint.set_text, f"yt-dlp : {line[:140]}"
                ),
            )

        def done(result: tuple[bool, str] | None = None) -> None:
            ok, message = result or (False, "yt-dlp n’a rien renvoyé.")
            prefix = "yt-dlp : " if ok else "yt-dlp a échoué : "
            self.engine_hint.set_text(prefix + message[:180])
            self._refresh_now()

        self._run_thread(work, done, self._show_error)


    def _on_download_context_closed(self, popover: Gtk.PopoverMenu) -> None:
        if self._download_context_popover is not popover:
            return
        self._download_context_popover = None
        pending = self._pending_download_refresh
        self._pending_download_refresh = None
        if pending is not None and not self._closing:
            self._populate_downloads(*pending)

    def _on_download_context_pressed(
        self,
        gesture: Gtk.GestureClick,
        n_press: int,
        x: float,
        y: float,
        popover: Gtk.PopoverMenu,
    ) -> None:
        if n_press != 1:
            return
        if (
            self._download_context_popover is not None
            and self._download_context_popover is not popover
        ):
            self._download_context_popover.popdown()
        self._download_context_popover = popover
        rectangle = Gdk.Rectangle()
        rectangle.x = int(x)
        rectangle.y = int(y)
        rectangle.width = 1
        rectangle.height = 1
        popover.set_pointing_to(rectangle)
        popover.popup()
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _attach_grabber_context_menu(
        self, row: Adw.ActionRow, item: dict[str, Any]
    ) -> None:
        """Attach the domain whitelist action to a Grabber result."""

        domain = source_host_name(item)
        # Never offer to whitelist a transient YouTube video id or another
        # value that is clearly not a host.  source_host_name() already maps
        # YouTube CDN/origin URLs to youtube.com when that information exists.
        usable_domain = bool(domain and ("." in domain or domain == "localhost"))

        actions = Gio.SimpleActionGroup()
        whitelist_action = Gio.SimpleAction.new("add-domain", None)
        whitelist_action.set_enabled(usable_domain)
        whitelist_action.connect(
            "activate",
            lambda *_args, grabber_item=item: self._add_grabber_domain_to_whitelist(
                grabber_item
            ),
        )
        actions.add_action(whitelist_action)

        menu = Gio.Menu()
        label = (
            f"Ajouter « {domain} » à la whitelist"
            if usable_domain
            else "Domaine d’origine indisponible"
        )
        menu.append(label, "grabber.add-domain")

        row.insert_action_group("grabber", actions)
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_has_arrow(True)
        popover.set_autohide(True)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_parent(row)
        popover.connect("closed", self._on_grabber_context_closed)

        gesture = Gtk.GestureClick()
        gesture.set_button(3)
        gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        gesture.connect("pressed", self._on_grabber_context_pressed, popover)
        row.add_controller(gesture)

    def _on_grabber_context_closed(self, popover: Gtk.PopoverMenu) -> None:
        if self._grabber_context_popover is popover:
            self._grabber_context_popover = None

    def _on_grabber_context_pressed(
        self,
        gesture: Gtk.GestureClick,
        n_press: int,
        x: float,
        y: float,
        popover: Gtk.PopoverMenu,
    ) -> None:
        if n_press != 1:
            return
        if (
            self._grabber_context_popover is not None
            and self._grabber_context_popover is not popover
        ):
            self._grabber_context_popover.popdown()
        self._grabber_context_popover = popover
        rectangle = Gdk.Rectangle()
        rectangle.x = int(x)
        rectangle.y = int(y)
        rectangle.width = 1
        rectangle.height = 1
        popover.set_pointing_to(rectangle)
        popover.popup()
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _add_grabber_domain_to_whitelist(self, item: dict[str, Any]) -> None:
        """Persist the source domain of one Grabber result, without duplicates."""

        domain = source_host_name(item)
        if not domain or ("." not in domain and domain != "localhost"):
            self._show_error(
                JDAPIError("Le domaine d’origine de ce lien est indisponible.")
            )
            return

        domains = self.config.grabber_domain_whitelist
        if domain in domains:
            message = f"{domain} est déjà dans la whitelist"
        else:
            self.config.grabber_domain_whitelist = [*domains, domain]
            if not self._save_grabber_options():
                return
            message = f"{domain} ajouté à la whitelist"

        self._sync_grabber_option_switches()
        self._populate_grabber(self._grabber_items)

    def _clear_grabber(self, *_args: Any) -> None:
        link_ids = [
            int(link_id)
            for _row, _check, link_id in self._grabber_rows
            if link_id is not None
        ]
        if not link_ids:
            return

        def work() -> Any:
            self._ensure_backend()
            return self.api.remove_grabber_links(link_ids, [])

        def done(_result: Any) -> None:
            self._selected_grabber_ids.difference_update(link_ids)
            self._refresh_now()

        self._run_thread(work, done, self._show_error)

    def _export_videos(self, *_args: Any) -> None:
        """Manually move completed video downloads to ~/Videos/.DEV."""
        video_extensions = {
            ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv",
            ".mpeg", ".mpg", ".webm", ".m4v", ".ogv",
        }
        candidates: list[tuple[int, Path]] = []
        for item in self._download_items:
            if not (bool(item.get("finished")) or status_text(item) == "Terminé"):
                continue
            try:
                link_id = int(item.get("uuid"))
            except (TypeError, ValueError):
                continue
            path = self._download_file_path(item)
            if path is not None and path.is_file() and path.suffix.lower() in video_extensions:
                candidates.append((link_id, path))
        if not candidates:
            self.engine_hint.set_text("Aucune vidéo terminée à exporter")
            return
        destination = Path.home() / "Videos" / ".DEV"
        def work() -> list[tuple[int, Path]]:
            destination.mkdir(parents=True, exist_ok=True)
            moved: list[tuple[int, Path]] = []
            for link_id, source in candidates:
                source = source.resolve()
                if source.parent == destination.resolve():
                    moved.append((link_id, source))
                    continue
                target = destination / source.name
                if target.exists():
                    stem, suffix, index = source.stem, source.suffix, 2
                    while (destination / f"{stem} ({index}){suffix}").exists():
                        index += 1
                    target = destination / f"{stem} ({index}){suffix}"
                shutil.move(str(source), str(target))
                moved.append((link_id, target))
            return moved
        def done(moved: list[tuple[int, Path]]) -> None:
            stored = self.config.data.setdefault("moved_video_paths", {})
            for link_id, target in moved:
                self._download_file_overrides[link_id] = target
                if isinstance(stored, dict):
                    stored[str(link_id)] = str(target)
            try:
                self.config.save()
            except OSError as exc:
                self._show_error(exc)
            count = len(moved)
            self.engine_hint.set_text(
                f"{count} vidéo{'s' if count > 1 else ''} exportée{'s' if count > 1 else ''} vers {destination}"
            )
            self._refresh_now()
        self._run_thread(work, done, self._show_error)

    def _remove_finished_downloads(self, *_args: Any) -> None:
        """Remove only completed queue entries; keep their local files."""
        link_ids = [
            int(item["uuid"])
            for item in self._download_items
            if item.get("uuid") is not None
            and (bool(item.get("finished")) or status_text(item) == "Terminé")
        ]
        if not link_ids:
            self.engine_hint.set_text("Aucun téléchargement terminé")
            return

        def work() -> Any:
            self._ensure_backend()
            return self.api.remove_downloads(link_ids, [])

        self._run_thread(work, lambda _result: self._refresh_now(), self._show_error)

    def _request_favicon(self, host: str) -> None:
        if not host or host in self._favicon_data or host in self._favicon_loading:
            return
        self._favicon_loading.add(host)

        def work() -> None:
            try:
                data = fetch_favicon(host)
            except Exception:
                data = None
            GLib.idle_add(self._favicon_loaded, host, data)

        threading.Thread(target=work, name="grabber-favicon", daemon=True).start()

    def _favicon_loaded(self, host: str, data: bytes | None) -> bool:
        self._favicon_loading.discard(host)
        self._favicon_data[host] = data
        if not data:
            return GLib.SOURCE_REMOVE
        try:
            texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
        except Exception:
            return GLib.SOURCE_REMOVE
        self._favicon_textures[host] = texture
        for image in self._favicon_images.get(host, []):
            image.set_paintable(texture)
            image.set_visible(True)
        return GLib.SOURCE_REMOVE

    def _host_badge(self, host: str) -> Gtk.Box:
        """Return a fixed-size host tile with a normalized icon and label."""
        badge = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        badge.add_css_class("host-badge")
        badge.set_size_request(112, 64)
        badge.set_homogeneous(False)
        badge.set_halign(Gtk.Align.CENTER)
        badge.set_valign(Gtk.Align.CENTER)
        badge.set_hexpand(False)
        badge.set_vexpand(False)

        icon_frame = Gtk.Overlay()
        icon_frame.add_css_class("host-favicon-frame")
        icon_frame.set_size_request(24, 24)
        icon_frame.set_halign(Gtk.Align.CENTER)
        icon_frame.set_valign(Gtk.Align.CENTER)
        fallback = Gtk.Image.new_from_icon_name("web-browser-symbolic")
        fallback.set_pixel_size(18)
        fallback.set_size_request(20, 20)
        fallback.set_halign(Gtk.Align.CENTER)
        fallback.set_valign(Gtk.Align.CENTER)
        fallback.add_css_class("host-favicon-fallback")

        icon = Gtk.Picture()
        icon.set_size_request(20, 20)
        icon.set_can_shrink(True)
        icon.set_hexpand(False)
        icon.set_vexpand(False)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.CENTER)
        icon.add_css_class("host-favicon")
        icon.set_visible(False)
        if hasattr(icon, "set_content_fit") and hasattr(Gtk, "ContentFit"):
            icon.set_content_fit(Gtk.ContentFit.CONTAIN)
        icon.set_tooltip_text(f"Service hôte : {host}")
        texture = self._favicon_textures.get(host)
        if texture is not None:
            icon.set_paintable(texture)
            icon.set_visible(True)
        else:
            self._favicon_images.setdefault(host, []).append(icon)
            self._request_favicon(host)
        icon_frame.set_child(fallback)
        icon_frame.add_overlay(icon)
        badge.append(icon_frame)

        # Compact host names by removing common public suffixes (com, net, sx,
        # etc.) from the visual label; the full hostname remains in the tooltip.
        host_label = host
        normalized_host = host.lower().removeprefix("www.")
        parts = normalized_host.split(".")
        compound_suffixes = {"co.uk", "org.uk", "com.au", "net.au", "co.jp", "com.br"}
        if len(parts) >= 3 and ".".join(parts[-2:]) in compound_suffixes:
            host_label = ".".join(parts[:-2])
        elif len(parts) >= 2 and (len(parts[-1]) <= 3 or parts[-1] in {"download", "files", "hosting"}):
            host_label = ".".join(parts[:-1])
        else:
            host_label = normalized_host
        label = Gtk.Label(label=host_label)
        label.set_xalign(0.5)
        label.set_halign(Gtk.Align.CENTER)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(12)
        label.set_single_line_mode(True)
        label.set_tooltip_text(f"Service hôte : {host}")
        label.add_css_class("host-label")
        badge.append(label)
        return badge

    def _set_download_package_dirs(self, packages: list[dict[str, Any]]) -> None:
        self._download_package_dirs = {}
        for package in packages:
            package_id = package.get("uuid")
            save_to = package.get("saveTo") or package.get("save_to")
            if package_id is None or not save_to:
                continue
            directory = Path(str(save_to)).expanduser()
            if not directory.is_absolute():
                directory = Path(self.config.download_dir).expanduser() / directory
            self._download_package_dirs[str(package_id)] = directory

    def _record_download_progress(self, items: list[dict[str, Any]]) -> None:
        """Keep a short frontend-side transfer history for reliable ETAs."""
        now = time.monotonic()
        active_ids: set[int] = set()
        cutoff = now - 30.0
        for item in items:
            try:
                link_id = int(item["uuid"])
            except (KeyError, TypeError, ValueError):
                continue
            total = as_number(item.get("bytesTotal"), -1)
            if total <= 0:
                continue
            loaded = max(0, as_number(item.get("bytesLoaded"), 0))
            active_ids.add(link_id)
            samples = self._download_eta_samples.setdefault(link_id, [])
            if samples and loaded < samples[-1][1]:
                # A reset or a newly renamed retry starts a new measurement.
                samples.clear()
            if not samples or loaded != samples[-1][1]:
                samples.append((now, loaded))
            samples[:] = [sample for sample in samples if sample[0] >= cutoff]
            if len(samples) > 12:
                del samples[:-12]

        self._download_eta_samples = {
            link_id: samples
            for link_id, samples in self._download_eta_samples.items()
            if link_id in active_ids
        }

    def _observed_download_speed(self, item: dict[str, Any]) -> int | None:
        try:
            link_id = int(item["uuid"])
        except (KeyError, TypeError, ValueError):
            return None
        samples = self._download_eta_samples.get(link_id, [])
        if len(samples) < 2:
            return None
        first_time, first_loaded = samples[0]
        last_time, last_loaded = samples[-1]
        elapsed = last_time - first_time
        transferred = last_loaded - first_loaded
        if elapsed <= 0 or transferred <= 0:
            return None
        return max(1, int(transferred / elapsed))

    def _download_file_path(self, item: dict[str, Any]) -> Path | None:
        try:
            override = self._download_file_overrides.get(int(item.get("uuid")))
        except (TypeError, ValueError):
            override = None
        if override is not None and override.is_file():
            return override
        raw_name = str(item.get("name") or "").strip()
        if not raw_name:
            return None
        name = Path(raw_name).name
        if not name or name == ".":
            return None

        root = Path(self.config.download_dir).expanduser()
        package_id = item.get("packageUUID")
        if package_id is None:
            package_id = item.get("packageUuid")
        directory = self._download_package_dirs.get(str(package_id))
        if directory is None:
            directory = root

        finished = bool(item.get("finished"))
        for key in ("filePath", "file_path", "localFile", "local_file"):
            value = item.get(key)
            if value:
                candidate = Path(str(value)).expanduser()
                candidate = candidate if candidate.is_absolute() else directory / candidate
                if candidate.is_dir():
                    candidate /= name
                candidates = (
                    (candidate, candidate.with_name(candidate.name + ".part.e2e"), candidate.with_name(candidate.name + ".part"))
                    if finished
                    else (candidate.with_name(candidate.name + ".part.e2e"), candidate.with_name(candidate.name + ".part"), candidate)
                )
                for possible in candidates:
                    if possible.is_file():
                        return possible

        # Prefer the active partial file. This matters when the user deletes a
        # link while JDownloader is still writing its ``.part`` file.
        candidate = directory / name
        candidates = (
            (candidate, candidate.with_name(candidate.name + ".part.e2e"), candidate.with_name(candidate.name + ".part"))
            if finished
            else (candidate.with_name(candidate.name + ".part.e2e"), candidate.with_name(candidate.name + ".part"), candidate)
        )
        for possible in candidates:
            if possible.is_file():
                return possible

        # Some JDownloader builds omit the package destination in a finished
        # link response. Only use a fallback when the filename is unique, so
        # another download with the same name can never be removed by mistake.
        try:
            matches = [
                path
                for candidate_name in (name + ".part.e2e", name + ".part", name)
                for path in root.rglob(candidate_name)
                if path.is_file()
            ]
        except OSError:
            matches = []
        if len(matches) == 1:
            return matches[0]

        # JDownloader returns the final filename in ``name``. Restricting it
        # to its basename prevents a malformed API value from escaping the
        # selected download directory.
        return candidate

    @staticmethod
    def _download_artifact_paths(
        path: Path, item: dict[str, Any]
    ) -> tuple[Path, ...]:
        """Return this link's final file and exact JDownloader sidecars."""

        name = path.name
        base_name = name
        for suffix in (".part.e2e", ".part"):
            if base_name.endswith(suffix):
                base_name = base_name[: -len(suffix)]
                break
        if not base_name:
            return (path,)
        return tuple(
            dict.fromkeys(
                (
                    path.with_name(base_name),
                    path.with_name(base_name + ".part"),
                    path.with_name(base_name + ".part.e2e"),
                )
            )
        )

    def _open_download_folder(self, item: dict[str, Any]) -> None:
        path = self._download_file_path(item)
        if path is not None:
            directory = path.parent
        else:
            directory = Path(self.config.download_dir).expanduser()
        directory = directory.expanduser()
        if not directory.is_dir():
            self._show_error(
                JDAPIError(f"Le dossier du téléchargement est introuvable : {directory}")
            )
            return
        try:
            subprocess.Popen(
                ["nautilus", str(directory)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError:
            try:
                Gio.AppInfo.launch_default_for_uri(
                    Gio.File.new_for_path(str(directory)).get_uri(),
                    None,
                )
            except GLib.Error as exc:
                self._show_error(
                    JDAPIError(f"Impossible d’ouvrir le dossier : {exc}")
                )
        except OSError as exc:
            self._show_error(JDAPIError(f"Impossible d’ouvrir le dossier : {exc}"))

    def _open_download_file(self, item: dict[str, Any]) -> None:
        path = self._download_file_path(item)
        if path is None or not path.is_file():
            self._show_error(
                JDAPIError("Le fichier n’est pas encore disponible sur le disque.")
            )
            return
        file_object = Gio.File.new_for_path(str(path))
        # An active download usually ends in ``.part``. Select the default
        # application from JDownloader's final filename so a media player or
        # document viewer can still be used before the rename is complete.
        final_name = str(item.get("name") or path.name)
        try:
            content_type, _uncertain = Gio.content_type_guess(final_name, None)
            if content_type:
                app_info = Gio.AppInfo.get_default_for_type(content_type, False)
                if app_info is not None:
                    app_info.launch([file_object], None)
                    return
            Gio.AppInfo.launch_default_for_uri(
                file_object.get_uri(),
                None,
            )
        except (AttributeError, GLib.Error, TypeError) as exc:
            self._show_error(JDAPIError(f"Impossible d’ouvrir le fichier : {exc}"))

    def _remove_empty_parent(self, path: Path) -> bool:
        """Remove only a safe, empty package subdirectory."""
        parent = path.parent
        try:
            parent_resolved = parent.resolve()
            root_resolved = Path(self.config.download_dir).expanduser().resolve()
            home_resolved = Path.home().resolve()
        except OSError:
            return False

        if parent_resolved in {root_resolved, home_resolved, Path("/")}:  # never remove Downloads itself
            return False
        try:
            parent_resolved.relative_to(root_resolved)
        except ValueError:
            return False
        try:
            parent.rmdir()
        except OSError as exc:
            if exc.errno in {errno.ENOTEMPTY, errno.EEXIST}:
                return False
            return False
        return True

    def _ask_delete_download_file(self, item: dict[str, Any]) -> None:
        path = self._download_file_path(item)
        if path is None:
            self._show_error(JDAPIError("Le chemin du fichier téléchargé est inconnu."))
            return

        name = str(item.get("name") or path.name)
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Supprimer définitivement le fichier ?",
            body=(
                f"Supprimer « {name} » et son dossier parent du disque ?\n\n"
                "Cette action est irréversible."
            ),
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("delete", "Supprimer")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(_dialog: Adw.MessageDialog, response: str) -> None:
            if response == "delete":
                self._delete_download_file(item, path)

        dialog.connect("response", on_response)
        dialog.present()

    def _delete_download_file(self, item: dict[str, Any], path: Path) -> None:
        link_id = item.get("uuid")
        if link_id is None:
            self._show_error(JDAPIError("L’identifiant du téléchargement est inconnu."))
            return

        def work() -> dict[str, Any]:
            deleted = False
            remove_error: str | None = None
            target = path

            # Stop this exact link before unlinking its partial file. Otherwise
            # a still-running JDownloader worker can recreate it immediately.
            try:
                self._ensure_backend()
                try:
                    self.api.set_download_enabled(False, [int(link_id)], [])
                except Exception as exc:
                    remove_error = str(exc)
                self.api.remove_downloads([int(link_id)], [])
            except Exception as exc:
                if remove_error:
                    remove_error += f" ; {exc}"
                else:
                    remove_error = str(exc)

            # Resolve the path again after stopping/removing the API entry: a
            # fast download may have switched from the final name to ``.part``
            # between the confirmation dialog and this worker.
            if not target.is_file():
                refreshed = self._download_file_path(item)
                if refreshed is not None:
                    target = refreshed

            local_error: str | None = None
            for artifact in self._download_artifact_paths(target, item):
                try:
                    artifact.unlink()
                    deleted = True
                except FileNotFoundError:
                    continue
                except IsADirectoryError as exc:
                    local_error = f"Le chemin attendu est un fichier : {artifact} ({exc})"
                    break
                except OSError as exc:
                    local_error = f"{artifact} ({exc})"
                    break
            if local_error and not deleted:
                raise JDAPIError(
                    f"Le lien a été retiré de la file, mais le fichier n’a pas pu être "
                    f"supprimé : {local_error}"
                )
            folder_removed = self._remove_empty_parent(target)
            return {
                "deleted": deleted,
                "folder_removed": folder_removed,
                "path": target,
                "remove_error": remove_error,
                "local_error": local_error,
            }

        def done(result: dict[str, Any]) -> None:
            if result["deleted"]:
                message = "Fichier supprimé définitivement du disque"
            else:
                message = "Le lien a été retiré ; le fichier était déjà absent"
            if result["folder_removed"]:
                message += " et son dossier vide a été supprimé"
            if result["remove_error"]:
                message += " ; l’entrée JDownloader n’a pas pu être retirée"
            if result["local_error"]:
                message += f" ; un fichier temporaire n’a pas pu être supprimé : {result['local_error']}"
            self.engine_hint.set_text(message)
            self._refresh_now()

        self._run_thread(work, done, self._show_error)

    def _on_download_check_toggled(
        self, check: Gtk.CheckButton, download_id: int
    ) -> None:
        if check.get_active():
            self._selected_download_ids.add(download_id)
        else:
            self._selected_download_ids.discard(download_id)
        if hasattr(self, "delete_selected_downloads_button"):
            self.delete_selected_downloads_button.set_sensitive(bool(self._selected_download_ids))
        if hasattr(self, "export_videos_button"):
            video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".mpeg", ".mpg", ".webm", ".m4v", ".ogv"}
            has_exportable_video = any(
                (bool(item.get("finished")) or status_text(item) == "Terminé")
                and (path := self._download_file_path(item)) is not None
                and path.is_file()
                and path.suffix.lower() in video_extensions
                for item in items
            )
            self.export_videos_button.set_sensitive(has_exportable_video)

    def _delete_selected_downloads(self, *_args: Any) -> None:
        selected = [
            item for item in self._download_items
            if item.get("uuid") is not None
            and int(item["uuid"]) in self._selected_download_ids
        ]
        if not selected:
            self._selected_download_ids.clear()
            self.delete_selected_downloads_button.set_sensitive(False)
            return

        count = len(selected)
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Supprimer {count} téléchargement{'s' if count > 1 else ''} ?",
            body=(
                "Les fichiers sélectionnés et leurs entrées JDownloader seront supprimés du disque.\n\n"
                "Cette action est irréversible."
            ),
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("delete", "Tout supprimer")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(_dialog: Adw.MessageDialog, response: str) -> None:
            if response != "delete":
                return
            targets = []
            for item in selected:
                path = self._download_file_path(item)
                if path is not None:
                    targets.append((item, path))
            if not targets:
                self._show_error(JDAPIError("Aucun chemin de fichier sélectionné n’est disponible."))
                return

            def work() -> dict[str, Any]:
                deleted = 0
                already_absent = 0
                errors: list[str] = []
                self._ensure_backend()
                for item, initial_path in targets:
                    link_id = int(item["uuid"])
                    target = initial_path
                    try:
                        try:
                            self.api.set_download_enabled(False, [link_id], [])
                        except Exception:
                            pass
                        self.api.remove_downloads([link_id], [])
                        if not target.is_file():
                            refreshed = self._download_file_path(item)
                            if refreshed is not None:
                                target = refreshed
                        removed_this = False
                        for artifact in self._download_artifact_paths(target, item):
                            try:
                                artifact.unlink()
                                removed_this = True
                            except FileNotFoundError:
                                continue
                        if removed_this:
                            deleted += 1
                        else:
                            already_absent += 1
                        self._remove_empty_parent(target)
                    except Exception as exc:
                        errors.append(f"{item.get('name') or link_id} : {exc}")
                return {"deleted": deleted, "absent": already_absent, "errors": errors}

            def done(result: dict[str, Any]) -> None:
                self._selected_download_ids.clear()
                self.delete_selected_downloads_button.set_sensitive(False)
                summary = f"{result['deleted']} fichier(s) supprimé(s)"
                if result["absent"]:
                    summary += f" ; {result['absent']} déjà absent(s)"
                if result["errors"]:
                    summary += f" ; {len(result['errors'])} erreur(s)"
                    summary += " — " + " ; ".join(result["errors"][:3])
                self.engine_hint.set_text(summary)
                self._refresh_now()

            self._run_thread(work, done, self._show_error)

        dialog.connect("response", on_response)
        dialog.present()

    def _keep_download_order(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Pin every row to the place it first appeared in.

        JDownloader reorders its own replies as links progress, and a row that
        moves while it downloads is exactly what the user notices.
        """

        order: list[int] = self.__dict__.setdefault("_download_row_order", [])
        known = set(order)
        for item in items:
            try:
                uuid = int(item.get("uuid"))
            except (TypeError, ValueError):
                continue
            if uuid not in known:
                order.append(uuid)
                known.add(uuid)
        rank = {uuid: place for place, uuid in enumerate(order)}

        def position(item: dict[str, Any]) -> int:
            try:
                return rank[int(item.get("uuid"))]
            except (TypeError, ValueError, KeyError):
                return len(order)

        return sorted(items, key=position)

    def _ytdlp_overlay(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Display links JDownloader gave up on using the bundled yt-dlp.

        The rows stay JDownloader rows: only the state they show comes from
        elsewhere, so a handled link looks like any other download.
        """

        def dropped_by_jd(candidate: dict[str, Any]) -> bool:
            if candidate.get("finished") or candidate.get("running"):
                return False
            if candidate.get("skipped"):
                return True
            return str(candidate.get("status") or "").upper() in {
                "ERROR",
                "OFFLINE",
                "TEMP_UNAVAILABLE",
            }

        if not items:
            return items
        jobs = self.__dict__.setdefault("_ytdlp_jobs", {})
        views: list[dict[str, Any]] = []
        for item in items:
            url = self._link_url(item)
            job = jobs.get(url) if url else None
            if job is None and url and ytdlp.handles(url, self.config.ytdlp_domains) and dropped_by_jd(item):
                path = self._download_file_path(item)
                if path is None or not path.is_file():
                    job = self._start_ytdlp_job(url, item, path)
            if job is None:
                views.append(item)
                continue
            view = dict(item)
            view["skipped"] = False
            view["enabled"] = True
            view["finished"] = bool(job["finished"])
            view["running"] = not job["finished"] and not job["error"]
            view["status"] = (
                "FINISHED" if job["finished"] else "ERROR" if job["error"] else "DOWNLOADING"
            )
            if job.get("total"):
                view["bytesTotal"] = job["total"]
                view["bytesLoaded"] = job["total"] if job["finished"] else job.get("loaded", 0)
            views.append(view)
        return views

    def _start_ytdlp_job(
        self, url: str, item: dict[str, Any], path: Path | None
    ) -> dict[str, Any]:
        """Run the bundled yt-dlp for one link and follow it from the row."""

        directory = path.parent if path is not None else Path(self.config.download_dir).expanduser()
        job: dict[str, Any] = {
            "url": url,
            "loaded": 0,
            "total": 0,
            "percent": -1,
            "finished": False,
            "error": False,
        }
        self._ytdlp_jobs[url] = job
        raw_uuid = item.get("uuid")

        def poked() -> bool:
            self._refresh_now()
            return False

        def progress(line: str) -> None:
            destination = ytdlp.parse_destination(line)
            if destination:
                self._download_file_overrides[int(raw_uuid)] = Path(destination)
            parsed = ytdlp.parse_progress(line)
            if parsed is None:
                return
            loaded, total = parsed
            job["loaded"], job["total"] = loaded, total
            job["percent"] = int(loaded * 100 / total) if total else 0

        def worker() -> None:
            try:
                ok, _message = ytdlp.download(
                    url,
                    directory,
                    log_path=ytdlp.job_log_path(url),
                    on_line=progress,
                )
            except Exception:
                ok = False
            job["finished"] = bool(ok)
            job["error"] = not ok
            if ok and job.get("total"):
                job["loaded"] = job["total"]
            GLib.idle_add(poked)

        threading.Thread(target=worker, daemon=True).start()
        return job


    def _number_label(self, position: int) -> Gtk.Label:
        """Numéro d'ordre de la ligne, dans la liste telle qu'affichée."""
        label = Gtk.Label(label=str(position))
        label.add_css_class("numeric")
        label.add_css_class("muted")
        label.set_valign(Gtk.Align.CENTER)
        label.set_xalign(1)
        label.set_size_request(24, -1)
        label.set_tooltip_text("Position dans la liste")
        return label

    def _populate_downloads(
        self, items: list[dict[str, Any]], packages: list[dict[str, Any]]
    ) -> None:
        items = self._ytdlp_overlay(items)
        items = self._keep_download_order(items)
        previous_items = list(self._download_items)
        self._record_download_progress(items)
        previous_active = any(
            not (bool(item.get("finished")) or status_text(item) == "Terminé")
            for item in previous_items
        )
        current_active = any(
            not (bool(item.get("finished")) or status_text(item) == "Terminé")
            for item in items
        )
        if previous_items and previous_active and not current_active and items:
            try:
                notification = Gio.Notification.new("Tous les téléchargements Grabber sont terminés")
                notification.set_body("La file de téléchargements est terminée.")
                self.get_application().send_notification("grabber-downloads-complete", notification)
            except (AttributeError, GLib.Error):
                pass
        total_bytes = sum(max(0, as_number(item.get("bytesTotal", 0))) for item in items)
        loaded_bytes = sum(max(0, as_number(item.get("bytesLoaded", 0))) for item in items)
        if hasattr(self, "global_progress"):
            fraction = min(1.0, loaded_bytes / total_bytes) if total_bytes else 0.0
            self.global_progress.set_fraction(fraction)
            self.global_progress_label.set_text(
                f"{round(fraction * 100)} %" if total_bytes else ""
            )
            total_speed = sum(max(0, as_number(item.get("speed", 0))) for item in items)
            remaining = max(0, total_bytes - loaded_bytes)
            eta = int(remaining / total_speed) if total_speed > 0 else None
            self.global_activity_label.set_text(
                f"{format_speed(total_speed)} · {format_duration_seconds(eta)}"
                if total_speed > 0 else ""
            )
        # The periodic poll rebuilds rows. Keep the current native context
        # menu open long enough for the user to choose an action instead of
        # replacing its parent row underneath it.
        if (
            self._download_context_popover is not None
            and self._download_context_popover.get_visible()
        ):
            self._pending_download_refresh = (list(items), list(packages))
            return
        self._download_items = list(items)
        current_download_ids = {
            int(item["uuid"]) for item in items if item.get("uuid") is not None
        }
        self._selected_download_ids.intersection_update(current_download_ids)
        if hasattr(self, "delete_selected_downloads_button"):
            self.delete_selected_downloads_button.set_sensitive(bool(self._selected_download_ids))
        self._set_download_package_dirs(packages)
        self._favicon_images = {}
        self._clear_list(self.download_list)
        for position, item in enumerate(items, start=1):
            row = Adw.ActionRow()
            name = str(item.get("name") or item.get("url") or "Lien sans nom")
            host = host_name(item)
            loaded = item.get("bytesLoaded", 0)
            total = item.get("bytesTotal", 0)
            speed = item.get("speed", 0)
            item_status = status_text(item)
            is_finished = bool(item.get("finished")) or item_status == "Terminé"
            if is_finished:
                # Dim the whole row: a finished download must stand out at a glance
                # from the ones still running.
                row.add_css_class("download-done")
                downloaded = format_bytes(loaded)
                subtitle = (
                    f"{downloaded} / {format_bytes(total)}"
                    if total
                    else downloaded
                )
            else:
                subtitle = (
                    f"{status_text(item)}  •  "
                    f"{format_bytes(loaded)} / {format_bytes(total)}"
                )
            row.set_title(name)
            row.set_subtitle(subtitle)
            row.set_activatable(False)
            row.set_tooltip_text("Utiliser les boutons d’action pour ouvrir le fichier ou son dossier")
            download_id = item.get("uuid")
            normalized_download_id = int(download_id) if download_id is not None else None
            check = Gtk.CheckButton()
            check.add_css_class("selection-mode")
            check.set_tooltip_text("Sélectionner ce téléchargement")
            check.set_active(
                normalized_download_id is not None
                and normalized_download_id in self._selected_download_ids
            )
            if normalized_download_id is not None:
                check.connect("toggled", self._on_download_check_toggled, normalized_download_id)
            else:
                check.set_sensitive(False)
            row.add_prefix(self._number_label(position))
            row.add_prefix(check)
            if host:
                row.add_prefix(self._host_badge(host))

            if is_finished:
                complete_icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
                complete_icon.set_tooltip_text("Téléchargement terminé")
                complete_icon.set_pixel_size(18)
                complete_icon.set_valign(Gtk.Align.CENTER)
                complete_icon.add_css_class("download-complete")
                row.add_suffix(complete_icon)
            else:
                progress = Gtk.ProgressBar()
                progress.set_fraction(progress_for(item))
                progress.set_size_request(150, -1)
                progress.set_valign(Gtk.Align.CENTER)
                row.add_suffix(progress)

                observed_speed = self._observed_download_speed(item)
                eta = estimate_eta_seconds(item, observed_speed)
                percent = progress_percent(item)
                percent_label = "— %" if percent is None else f"{percent} %"
                meta = Gtk.Label(
                    label=(
                        f"{format_speed(speed)}\n"
                        f"{percent_label} • ETA {format_duration_seconds(eta)}"
                    )
                )
                meta.set_xalign(1)
                meta.add_css_class("numeric")
                row.add_suffix(meta)

            self._attach_download_context_menu(row, item)
            self.download_list.append(row)
    def _populate_grabber(self, items: list[dict[str, Any]]) -> None:
        if self._grabber_context_popover is not None:
            self._grabber_context_popover.popdown()
            self._grabber_context_popover = None
        self._grabber_items = items
        current_ids = {
            int(item["uuid"])
            for item in items
            if item.get("uuid") is not None
        }
        self._selected_grabber_ids.intersection_update(current_ids)
        self._clear_list(self.grabber_list)
        self._grabber_rows = []
        visible_items = [item for item in items if self._matches_grabber_filter(item)]
        filter_label = next(
            (label for label, key in self.GRABBER_FILTERS if key == self._grabber_filter),
            "Tous les fichiers",
        )
        if visible_items:
            self.grabber_empty.set_text("Aucun lien analysé")
        elif self._grabber_filter == "all":
            self.grabber_empty.set_text("Aucun lien analysé")
        else:
            self.grabber_empty.set_text(f"Aucun fichier de type « {filter_label} »")
        self.grabber_select_all_button.set_sensitive(bool(visible_items))

        for position, item in enumerate(visible_items, start=1):
            row = Adw.ActionRow()
            row.add_prefix(self._number_label(position))
            check = Gtk.CheckButton()
            check.add_css_class("selection-mode")
            check.set_tooltip_text("Sélectionner ce fichier")
            # JDownloader's ``enabled`` means that the link is allowed to
            # download; it is not the selection state of this frontend.
            check.set_active(False)
            row.add_prefix(check)
            link_id = item.get("uuid")
            normalized_link_id = int(link_id) if link_id is not None else None
            if normalized_link_id is not None:
                check.set_active(normalized_link_id in self._selected_grabber_ids)
                check.connect(
                    "toggled",
                    self._on_grabber_check_toggled,
                    normalized_link_id,
                )
            name = str(item.get("name") or item.get("url") or "Lien sans nom")
            host = host_name(item)
            availability = str(item.get("availability") or "")
            total_value = as_number(item.get("bytesTotal"), -1)
            size = (
                f"Taille : {format_bytes(total_value)}"
                if total_value > 0
                else "Taille inconnue"
            )
            if host:
                row.add_prefix(self._host_badge(host))
            subtitle = "  •  ".join(str(part) for part in (availability, size) if part)
            row.set_title(name)
            row.set_subtitle(subtitle or "En attente d'analyse")
            row.set_activatable(False)
            self._attach_grabber_context_menu(row, item)
            self.grabber_list.append(row)
            self._grabber_rows.append((row, check, normalized_link_id))

    def _on_grabber_check_toggled(
        self, check: Gtk.CheckButton, link_id: int
    ) -> None:
        if check.get_active():
            self._selected_grabber_ids.add(link_id)
        else:
            self._selected_grabber_ids.discard(link_id)

    def _matches_grabber_filter(self, item: dict[str, Any]) -> bool:
        if self._grabber_filter != "all" and file_category(item) != self._grabber_filter:
            return False
        if not self.config.grabber_whitelist_enabled:
            return True
        patterns = normalize_domain_list(self.config.grabber_domain_whitelist)
        if not patterns:
            return False
        host = source_host_name(item)
        return any(domain_matches(host, pattern) for pattern in patterns)

    def _on_grabber_filter_toggle(self, button: Gtk.ToggleButton, key: str) -> None:
        if not button.get_active() or key == self._grabber_filter:
            return
        self._grabber_filter = key
        self.config.grabber_filter = key
        try:
            self.config.save()
        except OSError as exc:
            self._show_error(exc)
        self._populate_grabber(self._grabber_items)

    def _on_grabber_filter_changed(self, dropdown: Gtk.DropDown, *_args: Any) -> None:
        selected = dropdown.get_selected()
        if 0 <= selected < len(self.GRABBER_FILTERS):
            self._grabber_filter = self.GRABBER_FILTERS[selected][1]
            self.config.grabber_filter = self._grabber_filter
            try:
                self.config.save()
            except OSError as exc:
                self._show_error(exc)
            self._populate_grabber(self._grabber_items)

    @staticmethod
    def _clear_list(list_box: Gtk.ListBox) -> None:
        child = list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            list_box.remove(child)
            child = next_child

    def _set_controls_sensitive(self, sensitive: bool) -> None:
        self.start_button.set_sensitive(sensitive)
        self.stop_button.set_sensitive(sensitive)
        self.grabber_scan_button.set_sensitive(sensitive)
        if hasattr(self, "grabber_select_all_button"):
            self.grabber_select_all_button.set_sensitive(
                sensitive and bool(self._grabber_rows)
            )

    def _set_download_controller_state(self, running: bool) -> None:
        active = self.start_button if running else self.stop_button
        inactive = self.stop_button if running else self.start_button
        for button in (active, inactive):
            button.remove_css_class("suggested-action")
        active.set_tooltip_text(
            "Téléchargements en cours"
            if running
            else "Téléchargements arrêtés"
        )
        inactive.set_tooltip_text(
            "Arrêter les téléchargements"
            if running
            else "Démarrer les téléchargements"
        )

    def _set_online(self, state: str) -> None:
        self._known_online = True
        self._update_connection_indicators(
            "network-wired-symbolic", "online", "Connecté"
        )
        self.engine_hint.set_text("")
        normalized_state = state.upper()
        self._set_download_controller_state(
            normalized_state in {"RUNNING", "DOWNLOADING"}
            or "RUNNING" in normalized_state
            or "DOWNLOADING" in normalized_state
        )

    def _set_offline(self) -> None:
        self._known_online = False
        self._update_connection_indicators(
            "network-offline-symbolic", "offline", "Déconnecté"
        )
        self.engine_hint.set_text("")

    def _set_starting(self) -> None:
        self._update_connection_indicators(
            "network-transmit-receive-symbolic", "starting", "Connexion en cours"
        )
        self.engine_hint.set_text("")

    def _update_connection_indicators(
        self, icon_name: str, state_class: str, tooltip: str
    ) -> None:
        """Keep the JDownloader status icon synchronized on both page footers."""
        buttons = [
            getattr(self, "connection_button", None),
            getattr(self, "grabber_connection_button", None),
        ]
        for button in buttons:
            if button is None:
                continue
            image = button.get_child()
            if image is not None and hasattr(image, "set_from_icon_name"):
                image.set_from_icon_name(icon_name)
                image.set_tooltip_text(tooltip)
            for css_class in ("online", "offline", "starting"):
                button.remove_css_class(css_class)
            button.add_css_class(state_class)
            if state_class != "online":
                button.remove_css_class("suggested-action")
            button.set_tooltip_text(tooltip)

    def _show_error(self, exc: Exception) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Impossible d'effectuer l'opération",
            body=str(exc),
        )
        dialog.add_response("close", "Fermer")
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.present()

    def _open_settings(self, *_args: Any) -> None:
        open_settings_dialog(self)

    def _show_about(self, *_args: Any) -> None:
        """Ouvrir le dialogue « À propos » natif, icône de l'app comprise."""
        if hasattr(Adw, "AboutDialog"):
            about = Adw.AboutDialog(
                application_name="Grabber",
                application_icon="com.ogu.Grabber-simplified-v2",
                developer_name="ogu",
                version=APP_VERSION,
                comments="Interface libadwaita minimale pour JDownloader",
            )
            about.present(self)
            return
        dialog = Gtk.AboutDialog(
            transient_for=self,
            modal=True,
            program_name="Grabber",
            logo_icon_name="com.ogu.Grabber-simplified-v2",
            version=APP_VERSION,
            comments="Interface libadwaita minimale pour JDownloader",
            authors=["ogu"],
        )
        dialog.present()

    def _toggle_privacy_mode(self, *_args: Any) -> None:
        """Toggle the opaque privacy panel without changing the main page."""

        panel = getattr(self, "_privacy_panel", None)
        if panel is None:
            return
        hidden = panel.get_visible()
        panel.set_visible(not hidden)
        privacy_button = getattr(self, "privacy_button", None)
        if privacy_button is not None:
            privacy_button.set_tooltip_text(
                "Afficher l’interface" if not hidden else "Masquer l’interface"
            )

    def _on_preferences_applied(self, _result: Any) -> None:
        self._refresh_now()

    def _request_jdownloader_update(self, *_args: Any) -> None:
        request_jdownloader_update_dialog(self)
    def do_close_request(self) -> bool:
        if self._closing:
            return True

        active_statuses = {"Téléchargement", "Connexion", "Vérification", "Nouvelle tentative"}
        active_downloads = any(
            not (bool(item.get("finished")) or status_text(item) == "Terminé")
            and status_text(item) in active_statuses
            for item in self._download_items
        )
        if active_downloads and self.config.close_warning_enabled and not getattr(self, "_close_confirmed", False):
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Un téléchargement est en cours",
                body="Si tu quittes maintenant, le moteur JDownloader sera arrêté. Les téléchargements pourront reprendre au prochain lancement.",
            )
            dialog.add_response("cancel", "Annuler")
            dialog.add_response("quit", "Quitter quand même")
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            remember = Gtk.CheckButton(label="Ne plus demander")
            dialog.set_extra_child(remember)
            def close_response(_dialog: Adw.MessageDialog, response: str) -> None:
                if response != "quit":
                    dialog.close()
                    return
                if remember.get_active():
                    self.config.close_warning_enabled = False
                    try:
                        self.config.save()
                    except OSError as exc:
                        self._show_error(exc)
                self._close_confirmed = True
                dialog.close()
                self.close()
            dialog.connect("response", close_response)
            dialog.present()
            return True

        self._closing = True
        self._set_controls_sensitive(False)
        self._clipboard_monitor.stop()
        if self._clipboard_scan_source is not None:
            GLib.source_remove(self._clipboard_scan_source)
            self._clipboard_scan_source = None
        if self._delivery_retry_source is not None:
            GLib.source_remove(self._delivery_retry_source)
            self._delivery_retry_source = None
        self._pending_delivery = None

        # Let GTK perform the normal close immediately.  The cleanup is kept
        # alive by Gio.Application.hold(), so Java/JDownloader can still be
        # stopped after the native window has disappeared.
        self.set_visible(False)
        application = self.get_application()
        if application is not None:
            application.hold()

        def stop_engine() -> None:
            try:
                self.backend.stop(self.api)
            finally:
                GLib.idle_add(finish_shutdown)

        def finish_shutdown() -> bool:
            self._shutdown_complete = True
            if application is not None:
                application.release()
                application.quit()
            return GLib.SOURCE_REMOVE

        threading.Thread(
            target=stop_engine,
            name="grabber-shutdown",
            daemon=False,
        ).start()
        # False means that the default Adw/Gtk close handling may run now;
        # returning True here would keep the window around until the process
        # cleanup thread finished.
        return False


class JDAdwaitaApplication(Adw.Application):
    """Grabber, reachable through its own grabber:// URI scheme.

    Gio.ApplicationFlags.HANDLES_COMMAND_LINE is what makes that scheme work.
    The desktop file registers x-scheme-handler/grabber, the browser hands the
    URI over, and a second launch is forwarded over D-Bus to the instance that
    is already running instead of opening another window.
    """

    def __init__(self) -> None:
        super().__init__(
            application_id="com.ogu.Grabber",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.window: MainWindow | None = None
        self._silent_delivery_at = 0.0
        self.connect("activate", self._on_activate)
        self.connect("command-line", self._on_command_line)

    def _ensure_window(self) -> MainWindow:
        window = self.get_active_window()
        if window is None:
            window = MainWindow(self, AppConfig())
            self.window = window
        # Privacy mode is an explicit, temporary UI action.  Never restore
        # the opaque panel as the initial view when the application is opened.
        if hasattr(window, "_privacy_panel"):
            window._privacy_panel.set_visible(False)
        return window

    def _on_activate(self, *_args: Any) -> None:
        install_css()
        window = self._ensure_window()
        if time.monotonic() - self._silent_delivery_at < 2.0:
            # GApplication may emit "activate" right after a remote command
            # line.  The delivery already ran, so raising the window here would
            # steal a focus the user never asked for.
            return
        window.present()

    def _on_command_line(self, _application: Any, command_line: Any) -> int:
        install_css()
        arguments = list(command_line.get_arguments() or [])
        urls = urls_from_arguments(arguments[1:])
        existed = self.get_active_window() is not None
        window = self._ensure_window()
        if urls:
            # A new window takes the focus.  An already running Grabber only
            # takes it back when the user enabled that in the settings.
            focus = not existed or window.config.focus_on_delivery
            if not focus:
                self._silent_delivery_at = time.monotonic()
            window.deliver_urls(urls, focus=focus)
        else:
            self._silent_delivery_at = 0.0
            window.present()
        return 0


def _set_linux_process_name() -> None:
    """Make the frontend recognizable in GNOME System Monitor."""

    if not sys.platform.startswith("linux"):
        return
    try:
        # Keep Python-side process listings consistent with /proc/<pid>/comm.
        sys.argv[0] = "Grabber"
    except (IndexError, TypeError):
        pass
    try:
        libc = ctypes.CDLL(None)
        # Linux PR_SET_NAME changes /proc/<pid>/comm, which is what many
        # process managers display instead of Python's executable name.
        libc.prctl.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        libc.prctl.restype = ctypes.c_int
        libc.prctl(15, b"Grabber", 0, 0, 0)
    except (AttributeError, OSError, TypeError):
        pass


def main() -> int:
    _set_linux_process_name()
    GLib.set_prgname("Grabber")
    GLib.set_application_name("Grabber")
    Adw.init()
    # A private, versioned icon name avoids older icons in user themes.
    icon_env = os.environ.get("JD_ADWAITA_ICON_DIR")
    icon_dir = (
        Path(icon_env)
        if icon_env
        else Path(__file__).resolve().parents[3] / "share/icons/hicolor/512x512/apps"
    )
    display = Gdk.Display.get_default()
    if display is not None and icon_dir.is_dir():
        Gtk.IconTheme.get_for_display(display).add_search_path(str(icon_dir))
        Gtk.Window.set_default_icon_name("com.ogu.Grabber-simplified-v2")
    app = JDAdwaitaApplication()

    def stop_application(_signum: int, _frame: Any) -> None:
        # run.sh is an exec'ed Python process, so handling termination here
        # also covers Ctrl+C, terminal closure and a regular SIGTERM.
        app.quit()

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, stop_application)
    try:
        # sys.argv, never None: g_application_run() documents a NULL argv as
        # "command line handling is not required", so passing None would drop
        # the grabber:// URI and merely present the window.
        return app.run(sys.argv)
    finally:
        if app.window is not None and not app.window._shutdown_complete:
            app.window.backend.stop(app.window.api)
