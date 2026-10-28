from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from .api import JDAPIError, JDownloaderAPI
from .config import AppConfig


class JDownloaderProcess:
    """Launches JDownloader directly."""

    CANDIDATES = (
        Path.home() / ".jd_home" / "JDownloader.jar",
        Path.home() / ".config" / "jdownloader" / "JDownloader.jar",
        Path.home() / ".config" / "JDownloader" / "JDownloader.jar",
        Path.home() / "JDownloader" / "JDownloader.jar",
        Path.home() / "jdownloader" / "JDownloader.jar",
        Path("/opt/JDownloader/JDownloader.jar"),
        Path("/usr/share/jdownloader/JDownloader.jar"),
    )

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.process: subprocess.Popen[bytes] | None = None
        self.log_handle = None
        self._owns_process = False
        self._owned_jar: Path | None = None
        self._owned_process_group: int | None = None

    @property
    def _owner_marker(self) -> Path:
        return Path.home() / ".cache" / "jd-adwaita" / "owner.json"

    def _write_owner_marker(self) -> None:
        if self._owned_jar is None:
            return
        pid = self.process.pid if self.process is not None else None
        if pid is None:
            matches = self._find_existing_instances(self._owned_jar)
            pid = matches[0] if matches else None
        if pid is None:
            return
        marker = {
            "jar": str(self._owned_jar),
            "pid": pid,
            "process_group": self._owned_process_group,
        }
        try:
            self._owner_marker.parent.mkdir(parents=True, exist_ok=True)
            self._owner_marker.write_text(
                json.dumps(marker, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def _clear_owner_marker(self) -> None:
        try:
            self._owner_marker.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def _adopt_previous_owner(self, jar: Path) -> bool:
        """Recover ownership after a detached JVM survived the frontend."""
        try:
            marker = json.loads(self._owner_marker.read_text(encoding="utf-8"))
            marker_jar = Path(str(marker["jar"])).expanduser().resolve()
            jar_path = jar.expanduser().resolve()
        except (FileNotFoundError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return False

        if marker_jar != jar_path:
            return False
        if not self._find_existing_instances(jar_path):
            self._clear_owner_marker()
            return False

        self._owned_jar = jar_path
        try:
            self._owned_process_group = int(marker.get("process_group"))
        except (TypeError, ValueError):
            self._owned_process_group = None
        self._owns_process = True
        return True

    def find_jar(self) -> Path | None:
        runtime_dir = os.environ.get("JD_ADWAITA_RUNTIME_DIR")
        if runtime_dir:
            bundled_runtime_jar = Path(runtime_dir).expanduser() / "JDownloader.jar"
            if bundled_runtime_jar.is_file():
                return bundled_runtime_jar

        bundle_root = os.environ.get("JD_ADWAITA_BUNDLE_ROOT")
        if bundle_root:
            for candidate in (
                Path(bundle_root).expanduser() / "jdownloader" / "JDownloader.jar",
                Path(bundle_root).expanduser() / "JDownloader.jar",
            ):
                if candidate.is_file():
                    return candidate

        configured = self.config.jar_path
        if configured:
            candidate = Path(configured).expanduser()
            if candidate.is_file():
                return candidate
        for candidate in self.CANDIDATES:
            if candidate.is_file():
                return candidate
        return None

    def _java(self) -> str:
        bundled_java = os.environ.get("JD_ADWAITA_JAVA_PATH")
        if bundled_java and Path(bundled_java).expanduser().is_file():
            return str(Path(bundled_java).expanduser())

        bundle_root = os.environ.get("JD_ADWAITA_BUNDLE_ROOT")
        if bundle_root:
            candidate = Path(bundle_root).expanduser() / "java" / "bin" / "java"
            if candidate.is_file():
                return str(candidate)

        configured = self.config.java_path
        if configured and Path(configured).expanduser().exists():
            return str(Path(configured).expanduser())
        found = shutil.which("java")
        if found:
            return found
        raise JDAPIError("Java est introuvable. Installe jre-openjdk.")

    @property
    def cache_log_path(self) -> Path:
        """Console output of the engine, appended to for the whole session."""
        return Path.home() / ".cache" / "jd-adwaita" / "jdownloader.log"

    def java_binary(self) -> str:
        return self._java()

    def is_child_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @staticmethod
    def _command_line(proc_dir: Path) -> list[str]:
        try:
            raw = (proc_dir / "cmdline").read_bytes()
        except OSError:
            return []
        return [os.fsdecode(part) for part in raw.split(b"\0") if part]

    def _find_existing_instances(self, jar: Path) -> list[int]:
        """Find all JDownloader processes using this runtime directory."""
        try:
            jar_path = jar.expanduser().resolve()
        except OSError:
            jar_path = jar.expanduser()
        runtime_path = jar_path.parent
        core_path = runtime_path / "Core.jar"
        targets = {jar_path, core_path}

        try:
            proc_entries = Path("/proc").iterdir()
        except OSError:
            return []

        matches: list[int] = []

        for proc_dir in proc_entries:
            if not proc_dir.name.isdigit():
                continue
            try:
                pid = int(proc_dir.name)
            except ValueError:
                continue
            if pid == os.getpid():
                continue

            command_line = self._command_line(proc_dir)
            if not command_line:
                continue

            matched = False
            for token in command_line:
                try:
                    if Path(token).is_absolute() and Path(token).resolve() in targets:
                        matched = True
                        break
                except OSError:
                    continue

            if not matched:
                for index, token in enumerate(command_line[:-1]):
                    if token not in {"-jar", "--jar"}:
                        continue
                    candidate = Path(command_line[index + 1])
                    if not candidate.is_absolute():
                        candidate = runtime_path / candidate
                    try:
                        if candidate.resolve() in targets:
                            matched = True
                            break
                    except OSError:
                        continue

            try:
                proc_cwd = Path(os.readlink(proc_dir / "cwd")).resolve()
            except OSError:
                proc_cwd = None
            if not matched and proc_cwd == runtime_path and any(
                "JDownloader.jar" in token
                or "Core.jar" in token
                or "org.jdownloader" in token.lower()
                for token in command_line
            ):
                matched = True

            if matched:
                matches.append(pid)
        return matches

    def _find_existing_instance(self, jar: Path) -> int | None:
        """Find one JDownloader process already using this runtime directory."""
        matches = self._find_existing_instances(jar)
        return matches[0] if matches else None

    def _process_group_pids(self, process_group: int | None) -> set[int]:
        if process_group is None or process_group <= 1:
            return set()
        try:
            proc_entries = Path("/proc").iterdir()
        except OSError:
            return set()

        pids: set[int] = set()
        for proc_dir in proc_entries:
            if not proc_dir.name.isdigit():
                continue
            try:
                pid = int(proc_dir.name)
                if pid != os.getpid() and os.getpgid(pid) == process_group:
                    pids.add(pid)
            except (OSError, ValueError):
                continue
        return pids

    def _owned_pids(self) -> set[int]:
        pids = self._process_group_pids(self._owned_process_group)
        if self.process is not None and self.process.poll() is None:
            pids.add(self.process.pid)
        if self._owned_jar is not None:
            pids.update(self._find_existing_instances(self._owned_jar))
        return {pid for pid in pids if pid != os.getpid()}

    def _signal_owned(self, signum: int) -> None:
        process_group = self._owned_process_group
        if process_group is not None and process_group > 1:
            try:
                if process_group != os.getpgrp():
                    os.killpg(process_group, signum)
            except (OSError, ProcessLookupError):
                pass

        for pid in self._owned_pids():
            try:
                os.kill(pid, signum)
            except (OSError, ProcessLookupError):
                pass

    def _stop_owned_processes(self) -> None:
        """Stop the launcher and any detached JVM from the owned runtime."""
        process = self.process
        graceful_deadline = time.monotonic() + 1.5
        while time.monotonic() < graceful_deadline:
            if process is not None and process.poll() is None:
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
            if not self._owned_pids():
                return
            time.sleep(0.1)

        self._signal_owned(signal.SIGTERM)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            if process is not None and process.poll() is None:
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
            if not self._owned_pids():
                return
            time.sleep(0.1)

        self._signal_owned(signal.SIGKILL)
        if process is not None:
            try:
                process.wait(timeout=1)
            except (subprocess.TimeoutExpired, OSError):
                pass

    def start_and_wait(
        self,
        api: JDownloaderAPI,
        timeout: float = 180.0,
        _retry_clean_exit: bool = False,
    ) -> None:
        jar = self.find_jar()
        if api.ping():
            # The embedded mode owns only a process started by this frontend,
            # or one recovered through its own marker after a previous crash.
            # Never silently adopt an arbitrary system JDownloader instance.
            if self._owns_process:
                return
            if jar is not None and self._adopt_previous_owner(jar):
                return
            raise JDAPIError(
                "Une autre instance de JDownloader utilise déjà l’API locale. "
                "Ferme-la avant de lancer Grabber."
            )
        if jar is None:
            raise JDAPIError(
                "JDownloader.jar est introuvable. Ouvre Réglages pour indiquer son chemin."
            )

        # Recover only a JVM that this application previously launched.  An
        # unrelated existing process is reported below instead of being
        # adopted and killed when Grabber closes.
        recovered = self._adopt_previous_owner(jar)

        log_dir = Path.home() / ".cache" / "jd-adwaita"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.cache_log_path
        existing_pid = self._find_existing_instance(jar)

        child_running = self.is_child_running()
        if existing_pid is None and not child_running:
            self.log_handle = log_path.open("ab")
            command = [
                self._java(),
                "-Djava.awt.headless=true",
                "-jar",
                str(jar),
                "-norestart",
            ]
            try:
                self.process = subprocess.Popen(
                    command,
                    cwd=str(jar.parent),
                    stdin=subprocess.DEVNULL,
                    stdout=self.log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                self._owns_process = True
                self._owned_jar = jar.expanduser().resolve()
                try:
                    self._owned_process_group = os.getpgid(self.process.pid)
                except OSError:
                    self._owned_process_group = None
                self._write_owner_marker()
            except OSError as exc:
                self.log_handle.close()
                self.log_handle = None
                raise JDAPIError(f"Impossible de lancer JDownloader : {exc}") from exc
        elif existing_pid is not None and not child_running and not recovered:
            raise JDAPIError(
                f"Une instance existante (PID {existing_pid}) utilise déjà ce runtime. "
                "Ferme-la avant de lancer Grabber."
            )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if api.ping():
                return

            if self.process is not None and self.process.poll() is not None:
                returncode = self.process.returncode
                other_pid = self._find_existing_instance(jar)
                if other_pid is not None:
                    existing_pid = other_pid
                    self.process = None
                    # JDownloader's bootstrapper may have handed the runtime
                    # to a detached JVM. It is still ours because no instance
                    # existed when we launched it.
                    self._close_log()
                    time.sleep(0.5)
                    continue
                if returncode == 0 and not _retry_clean_exit:
                    self._close_log()
                    self.process = None
                    self._owns_process = False
                    self._clear_owner_marker()
                    self._owned_jar = None
                    self._owned_process_group = None
                    return self.start_and_wait(
                        api,
                        timeout=timeout,
                        _retry_clean_exit=True,
                    )
                detail = ""
                try:
                    detail = log_path.read_text(encoding="utf-8", errors="replace")[-500:]
                except OSError:
                    pass
                suffix = f"\n\nDernières lignes du journal :\n{detail}" if detail else ""
                raise JDAPIError(
                    f"JDownloader s'est arrêté avant de rendre l'API locale "
                    f"(code de sortie {returncode}).{suffix}"
                )
            time.sleep(0.5)
        detail = ""
        try:
            detail = log_path.read_text(encoding="utf-8", errors="replace")[-500:]
        except OSError:
            pass
        suffix = f"\nDernières lignes du journal :\n{detail}" if detail else ""
        instance_note = ""
        if existing_pid is not None:
            instance_note = (
                f" Une instance existante (PID {existing_pid}) utilise déjà ce runtime ; "
                "arrête-la si elle est bloquée."
            )
        raise JDAPIError(
            f"JDownloader ne répond pas à l'API locale après {timeout:g} secondes."
            + instance_note
            + " Vérifie que deprecatedapienabled est activé."
            + suffix
        )

    def stop(self, api: JDownloaderAPI | None = None) -> None:
        if not self._owns_process:
            self._close_log()
            return

        try:
            if api is not None:
                try:
                    if api.ping():
                        api.exit_jdownloader()
                except JDAPIError:
                    pass

            self._stop_owned_processes()
        finally:
            self._owns_process = False
            self._clear_owner_marker()
            self._owned_jar = None
            self._owned_process_group = None
            self._close_log()

    def update(self, api: JDownloaderAPI | None = None, timeout: float = 45.0) -> str:
        """Run JDownloader's native updater without waiting indefinitely."""
        jar = self.find_jar()
        if jar is None:
            raise JDAPIError(
                "JDownloader.jar est introuvable. Ouvre Réglages pour indiquer son chemin."
            )

        if api is not None:
            try:
                if api.ping():
                    api.exit_jdownloader()
            except JDAPIError:
                pass

        # An instance not started by this frontend cannot be signalled by us;
        # give JDownloader a moment to release its runtime lock after the API
        # exit request before invoking the updater.
        if not self._owns_process:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline and self._find_existing_instance(jar):
                time.sleep(0.25)

        if self._owns_process:
            self._stop_owned_processes()
            self._owns_process = False
            self._clear_owner_marker()
            self._owned_jar = None
            self._owned_process_group = None
        self._close_log()

        log_dir = Path.home() / ".cache" / "jd-adwaita"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "jdownloader-update.log"
        command = [
            self._java(),
            "-Djava.awt.headless=true",
            "-jar",
            str(jar),
            "-update",
        ]
        try:
            log_handle = log_path.open("w", encoding="utf-8")
            updater = subprocess.Popen(
                command,
                cwd=str(jar.parent),
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as exc:
            raise JDAPIError(f"Impossible de lancer la mise à jour : {exc}") from exc

        no_update_markers = (
            "Repo is on head revision. No update available",
            "No Update. Auto Update is disabled",
        )
        update_success_markers = ("Self Update successful",)
        connection_error_markers = (
            "The Update Server is not available",
            "No Connection to the Internet",
            "NoConnectionException",
            "UnknownHostException",
        )

        result_message: str | None = None
        update_error: JDAPIError | None = None
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                try:
                    log_handle.flush()
                    detail = log_path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    detail = ""
                if any(marker in detail for marker in connection_error_markers):
                    update_error = JDAPIError(
                        "Le serveur de mise à jour de JDownloader est inaccessible."
                    )
                    break
                if any(marker in detail for marker in no_update_markers):
                    result_message = "JDownloader est déjà à jour."
                    break
                if any(marker in detail for marker in update_success_markers):
                    result_message = "JDownloader a été mis à jour."
                    break
                if updater.poll() is not None:
                    if updater.returncode == 0:
                        result_message = "Vérification terminée : aucune mise à jour signalée."
                        break
                    update_error = JDAPIError(
                        f"La mise à jour de JDownloader a échoué (code de sortie "
                        f"{updater.returncode})."
                    )
                    break
                time.sleep(0.25)
            else:
                result_message = (
                    "La vérification de mise à jour a été interrompue ; "
                    "JDownloader a été relancé."
                )
        finally:
            if updater.poll() is None:
                updater.terminate()
                try:
                    updater.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    updater.kill()
                    updater.wait(timeout=3)
            log_handle.close()

        if result_message is None and update_error is None:
            detail = ""
            try:
                detail = log_path.read_text(encoding="utf-8", errors="replace")[-500:]
            except OSError:
                pass
            suffix = f"\n\nDernières lignes du journal :\n{detail}" if detail else ""
            update_error = JDAPIError(f"La mise à jour de JDownloader a échoué.{suffix}")

        if api is not None:
            try:
                self.start_and_wait(api, timeout=90.0)
            except JDAPIError:
                if update_error is None:
                    raise
        if update_error is not None:
            raise update_error
        return result_message

    def _close_log(self) -> None:
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None
