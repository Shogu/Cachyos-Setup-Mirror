#!/usr/bin/env python3

import ctypes
import re
import shlex
import shutil
import socket
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Secret", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Secret  # noqa: E402

APP_ID = "io.gitlab.shogu.Pusher"
VERSION = "1.8.3"
ASKPASS = "/usr/lib/pusher-askpass"
REPO_URL = "https://gitlab.com/Shogu/CACHYOS-Setup.git"
REPO_SSH_URL = "git@gitlab.com:Shogu/CACHYOS-Setup.git"
REPO_SSH_443_URL = "ssh://git@altssh.gitlab.com:443/Shogu/CACHYOS-Setup.git"
BIG_FILE = 25 * 1024 * 1024
PUSH_ATTEMPTS = 3
REPO_NAME = "CACHYOS-Setup"
REPO_PATH = Path(GLib.get_home_dir()) / "Gitlab" / REPO_NAME
SSH_KEY = Path(GLib.get_home_dir()) / ".ssh" / "id_ed25519_gitlab"
SSH_KEYS_URL = "https://gitlab.com/-/user_settings/ssh_keys"
GIT_NAME = "Shogu"
GIT_EMAIL = "ugo.trevisiol@gmail.com"

SECRET_SCHEMA_ID = "io.gitlab.shogu.GitLabSync"

TOKEN_SCHEMA = Secret.Schema.new(
    SECRET_SCHEMA_ID,
    Secret.SchemaFlags.NONE,
    {"service": Secret.SchemaAttributeType.STRING},
)
TOKEN_ATTRS = {"service": "gitlab.com"}


class GitError(Exception):
    pass


def load_token():
    try:
        return Secret.password_lookup_sync(TOKEN_SCHEMA, TOKEN_ATTRS, None) or ""
    except GLib.Error:
        return ""


def store_token(token):
    Secret.password_store_sync(
        TOKEN_SCHEMA,
        TOKEN_ATTRS,
        Secret.COLLECTION_DEFAULT,
        "Jeton GitLab (Pusher)",
        token,
        None,
    )


def clear_token():
    Secret.password_clear_sync(TOKEN_SCHEMA, TOKEN_ATTRS, None)


NETWORK_HINTS = (
    "connection reset",
    "broken pipe",
    "unexpected disconnect",
    "hung up unexpectedly",
    "early eof",
    "rpc failed",
    "timed out",
    "connection closed",
    "network is unreachable",
    "could not resolve",
)


def is_network_error(message):
    lowered = message.lower()
    return any(hint in lowered for hint in NETWORK_HINTS)


def is_auth_error(message):
    lowered = message.lower()
    if is_network_error(message):
        return False
    return any(
        hint in lowered
        for hint in (
            "could not read username",
            "authentication failed",
            "terminal prompts disabled",
            "access denied",
            "403 forbidden",
            "permission denied",
            "could not read from remote repository",
            "host key verification failed",
        )
    )


def ssh_command():
    options = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        # IPQoS=none : certaines box et partages de connexion coupent les longs envois SSH
        # marqués « throughput » (Connection reset by peer / Broken pipe).
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=6",
        "-o", "TCPKeepAlive=yes",
        "-o", "IPQoS=none",
    ]
    if SSH_KEY.exists():
        options += ["-o", "IdentitiesOnly=yes", "-i", str(SSH_KEY)]
    return shlex.join(options)


def make_launcher():
    flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
    launcher = Gio.SubprocessLauncher.new(flags)
    launcher.setenv("GIT_TERMINAL_PROMPT", "0", True)
    launcher.setenv("LC_ALL", "C", True)
    launcher.setenv("GIT_SSH_COMMAND", ssh_command(), True)
    launcher.setenv("SSH_ASKPASS_REQUIRE", "never", True)
    token = load_token()
    if token:
        launcher.setenv("PUSHER_TOKEN", token, True)
        launcher.setenv("GIT_ASKPASS", ASKPASS, True)
    return launcher


def run_command(argv, cwd=None):
    launcher = make_launcher()
    if cwd is not None:
        launcher.set_cwd(str(cwd))
    proc = launcher.spawnv(argv)
    _ok, out, _err = proc.communicate_utf8(None, None)
    output = (out or "").rstrip()
    if not proc.get_successful():
        raise GitError(output or f"{shlex.join(argv)} a échoué")
    return output


def run_git(args, cwd=None):
    return run_command(["git", "-c", "core.quotePath=false"] + args, cwd=cwd)


def run_git_bytes(args, cwd=None):
    """Comme run_git mais renvoie la sortie brute en octets.

    Indispensable pour `git status -z` dont les séparateurs NUL seraient sinon
    tronqués par Gio.communicate_utf8() au premier octet \0 : sans ça, Pusher ne
    voyait que le premier fichier en attente tout en en poussant plusieurs.
    """
    launcher = make_launcher()
    if cwd is not None:
        launcher.set_cwd(str(cwd))
    proc = launcher.spawnv(["git", "-c", "core.quotePath=false"] + args)
    ok, out, _err = proc.communicate(None, None)
    data = out.get_data() if (ok and out) else b""
    if not ok:
        text = data.decode("utf-8", "replace").rstrip()
        raise GitError(text or f"{shlex.join(args)} a échoué")
    return data


PROGRESS_RE = re.compile(r"Writing objects:\s+(\d+)%.*?(?:,\s*([\d.]+ \w+)(?: \| ([\d.]+ \w+/s))?)?$")


def run_git_progress(args, on_progress):
    """git avec --progress : chaque ligne « Writing objects » remonte à on_progress(fraction, texte)."""
    launcher = make_launcher()
    launcher.set_cwd(str(REPO_PATH))
    proc = launcher.spawnv(["git", "-c", "core.quotePath=false"] + args)
    stream = proc.get_stdout_pipe()
    output, pending = [], ""
    while True:
        chunk = stream.read_bytes(4096, None).get_data()
        if not chunk:
            break
        pending += chunk.decode("utf-8", "replace")
        *lines, pending = re.split(r"[\r\n]", pending)
        for line in lines:
            match = PROGRESS_RE.search(line.strip())
            if match:
                percent, done, speed = match.groups()
                text = f"Envoi : {percent} %"
                if done:
                    text += f" — {done}"
                if speed:
                    text += f" à {speed}"
                on_progress(int(percent) / 100, text)
            elif line.strip():
                output.append(line.strip())
    proc.wait(None)
    if pending.strip():
        output.append(pending.strip())
    text = "\n".join(output)
    if not proc.get_successful():
        raise GitError(text or "git push a échoué")
    return text


def ensure_ssh_key():
    SSH_KEY.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not SSH_KEY.exists():
        run_command(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-N",
                "",
                "-C",
                f"pusher@{socket.gethostname()}",
                "-f",
                str(SSH_KEY),
            ]
        )
    return SSH_KEY.with_name(SSH_KEY.name + ".pub").read_text().strip()


def use_ssh_remote():
    if is_cloned():
        run_git(["remote", "set-url", "origin", REPO_SSH_URL], cwd=REPO_PATH)


def is_cloned():
    return (REPO_PATH / ".git").is_dir()


def clone_repo():
    REPO_PATH.parent.mkdir(parents=True, exist_ok=True)
    run_git(["clone", REPO_URL, str(REPO_PATH)])
    if SSH_KEY.exists():
        use_ssh_remote()


def trash_path(path):
    try:
        Gio.File.new_for_path(str(path)).trash(None)
    except GLib.Error:
        shutil.rmtree(path)


STATUS_LABELS = {
    "A": ("Ajouté", "list-add-symbolic"),
    "?": ("Nouveau", "list-add-symbolic"),
    "M": ("Modifié", "document-edit-symbolic"),
    "T": ("Modifié", "document-edit-symbolic"),
    "D": ("Supprimé", "user-trash-symbolic"),
    "R": ("Renommé", "document-save-as-symbolic"),
    "C": ("Copié", "edit-copy-symbolic"),
    "U": ("En conflit", "dialog-warning-symbolic"),
}


def pending_changes():
    """[(code, chemin)] : -z évite les guillemets et échappements octaux (accents, espaces)."""
    if not is_cloned():
        return []
    raw = run_git_bytes(
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=REPO_PATH
    ).decode("utf-8", "replace")
    entries = raw.split("\0")
    changes = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if "R" in xy or "C" in xy:
            index += 1
        code = "?" if xy == "??" else ("U" if "U" in xy else next(c for c in xy if c != " "))
        if code in "AM?" and xy[1] == "D":
            continue
        changes.append((code, path))
    return changes


def upload_size(changes):
    total, big = 0, []
    for code, path in changes:
        full = REPO_PATH / path
        if code == "D" or not full.is_file():
            continue
        size = full.stat().st_size
        total += size
        if size >= BIG_FILE:
            big.append((path, size, code))
    return total, big


def merge_base(branch):
    try:
        return run_git(["merge-base", "HEAD", f"origin/{branch}"], cwd=REPO_PATH).strip()
    except GitError:
        return ""


def exclude_paths(paths):
    exclude = REPO_PATH / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as handle:
        for path in paths:
            handle.write("/" + re.sub(r"([\\*?\[#!])", r"\\\1", path) + "\n")


def fetch_remote():
    run_git(["fetch", "--quiet", "origin"], cwd=REPO_PATH)


def operation_in_progress():
    """Opération Git interrompue ou conflit d’index : None si le dépôt est sain."""
    # Un conflit peut subsister dans l’index sans MERGE_HEAD (par exemple après
    # une opération interrompue ou un conflit de suppression). Le détecter avant
    # les actions qui regroupent les commits avec reset --soft.
    if run_git(["ls-files", "-u"], cwd=REPO_PATH).strip():
        return "unmerged"

    git_dir = REPO_PATH / ".git"
    if (git_dir / "rebase-merge").is_dir() or (git_dir / "rebase-apply").is_dir():
        return "rebase"
    if (git_dir / "MERGE_HEAD").exists():
        return "merge"
    if (git_dir / "CHERRY_PICK_HEAD").exists():
        return "cherry-pick"
    if (git_dir / "REVERT_HEAD").exists():
        return "revert"
    return None


OPERATION_MESSAGES = {
    "unmerged": "Conflit Git non résolu dans l’index — lancez « git status » et résolvez les chemins signalés avant de synchroniser",
    "rebase": "Rebasage Git en cours — terminez ou annulez l’opération dans le terminal",
    "merge": "Fusion Git en cours — terminez ou annulez l’opération dans le terminal",
    "cherry-pick": "Cherry-pick Git en cours — terminez ou annulez l’opération dans le terminal",
    "revert": "Annulation (revert) Git en cours — terminez ou annulez l’opération dans le terminal",
}


def current_branch():
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_PATH).strip()
    if branch == "HEAD":
        # Pendant un rebasage, HEAD est détachée : la vraie branche est notée dans .git.
        git_dir = REPO_PATH / ".git"
        for name in ("rebase-merge", "rebase-apply"):
            try:
                ref = (git_dir / name / "head-name").read_text().strip()
            except OSError:
                continue
            if ref.startswith("refs/heads/"):
                return ref[len("refs/heads/"):]
    return branch


def ahead_behind(branch):
    """Commits local-only / remote-only, relative to origin/<branch>."""
    try:
        counts = run_git(
            ["rev-list", "--left-right", "--count", f"{branch}...origin/{branch}"],
            cwd=REPO_PATH,
        )
        ahead_str, behind_str = counts.split()
        return int(ahead_str), int(behind_str)
    except GitError:
        return 0, 0


class Window(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Pusher")
        self.set_default_size(520, 560)
        self.set_size_request(360, 360)
        self.busy = False
        self.pending_files = []
        self.current_branch = ""
        self.ahead = 0
        self.behind = 0
        self.operation = None
        self.action_mode = "push"
        self.refresh_queued = False

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)

        toolbar = Adw.ToolbarView()
        self.toasts.set_child(toolbar)

        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        self.action_content = Adw.ButtonContent(icon_name="gitlab-symbolic", label="Push")
        self.push_button = Gtk.Button(
            child=self.action_content,
            tooltip_text=f"Envoyer les fichiers vers {REPO_NAME} sur GitLab",
        )
        self.push_button.add_css_class("suggested-action")
        self.push_button.connect("clicked", self.on_action_clicked)
        header.pack_start(self.push_button)

        refresh = Gtk.Button(
            icon_name="view-refresh-symbolic", tooltip_text="Actualiser l’état"
        )
        refresh.connect("clicked", lambda *_: self.refresh(check_remote=True))
        header.pack_end(refresh)

        menu = Gio.Menu()
        menu.append("Recloner le dépôt…", "app.reclone")
        menu.append("Connexion à GitLab…", "app.connect")
        menu.append("Jeton GitLab…", "app.token")
        menu.append("À propos de Pusher", "app.about")
        header.pack_end(
            Gtk.MenuButton(
                icon_name="open-menu-symbolic",
                menu_model=menu,
                tooltip_text="Menu principal",
            )
        )

        self.banner = Adw.Banner(revealed=False)
        toolbar.add_top_bar(self.banner)
        self.progress = Gtk.ProgressBar(visible=False)
        self.progress.add_css_class("osd")
        toolbar.add_top_bar(self.progress)

        self.stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE, vexpand=True
        )
        toolbar.set_content(self.stack)
        self.stack.add_named(self.build_welcome(), "welcome")
        self.stack.add_named(self.build_repo_page(), "repo")

        self.connect("notify::is-active", self.on_active_changed)
        self.refresh(check_remote=False)
        self.check_remote(auto_pull=True)

    def on_active_changed(self, *_args):
        if self.is_active():
            self.refresh(check_remote=False)

    # pages -----------------------------------------------------------------

    def build_welcome(self):
        status = Adw.StatusPage(
            icon_name=APP_ID,
            title=REPO_NAME,
            description=f"Le dépôt sera cloné dans {REPO_PATH}.",
        )
        clone = Gtk.Button(
            child=Adw.ButtonContent(
                icon_name="folder-download-symbolic", label="Cloner le dépôt"
            ),
            halign=Gtk.Align.CENTER,
        )
        clone.add_css_class("pill")
        clone.add_css_class("suggested-action")
        clone.connect("clicked", self.on_clone_clicked)
        self.clone_button = clone
        status.set_child(clone)
        return status

    def build_repo_page(self):
        page = Adw.PreferencesPage()

        group = Adw.PreferencesGroup(title="Dépôt")
        page.add(group)

        self.path_row = Adw.ActionRow(title="Dossier local", subtitle=str(REPO_PATH))
        self.path_row.add_prefix(Gtk.Image(icon_name="folder-symbolic"))
        open_button = Gtk.Button(
            icon_name="document-open-symbolic",
            valign=Gtk.Align.CENTER,
            tooltip_text="Ouvrir le dossier",
        )
        open_button.add_css_class("flat")
        open_button.connect("clicked", self.on_open_folder)
        self.path_row.add_suffix(open_button)
        self.path_row.set_activatable_widget(open_button)
        group.add(self.path_row)

        self.branch_row = Adw.ActionRow(title="Branche", subtitle="—")
        self.branch_row.add_prefix(Gtk.Image(icon_name="media-playlist-shuffle-symbolic"))
        group.add(self.branch_row)

        self.message_row = Adw.EntryRow(title="Message de commit")
        self.message_row.set_text("Mise à jour")
        group.add(self.message_row)

        self.changes_group = Adw.PreferencesGroup(title="Fichiers à envoyer")
        page.add(self.changes_group)
        self.changes_rows = []
        self.empty_row = Adw.ActionRow(
            title="Aucune modification", subtitle="Le dossier local est à jour."
        )
        self.empty_row.add_prefix(Gtk.Image(icon_name="object-select-symbolic"))
        self.changes_group.add(self.empty_row)

        self.deleted_group = Adw.PreferencesGroup(title="Fichiers supprimés")
        page.add(self.deleted_group)
        self.deleted_rows = []
        self.deleted_empty = Adw.ActionRow(
            title="Aucun fichier supprimé", subtitle="Rien à supprimer sur GitLab."
        )
        self.deleted_empty.add_prefix(Gtk.Image(icon_name="user-trash-symbolic"))
        self.deleted_group.add(self.deleted_empty)

        return page

    # helpers ---------------------------------------------------------------

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=5, use_markup=False))

    def show_error(self, heading, details):
        """Erreur détaillée dans une boîte de dialogue : texte complet, sélectionnable
        et copiable (une notification d'une ligne tronquait les messages Git)."""
        details = (details or "").strip() or "Erreur inconnue."
        dialog = Adw.AlertDialog(heading=heading)

        view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            left_margin=10,
            right_margin=10,
            top_margin=8,
            bottom_margin=8,
            css_classes=["card"],
        )
        view.get_buffer().set_text(details)
        scroller = Gtk.ScrolledWindow(
            child=view,
            min_content_height=80,
            max_content_height=260,
            propagate_natural_height=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        dialog.set_extra_child(scroller)
        dialog.add_response("copy", "Copier")
        dialog.add_response("close", "Fermer")
        dialog.set_default_response("close")
        dialog.set_close_response("close")

        def on_response(_dialog, response):
            if response == "copy":
                self.get_clipboard().set(details)
                self.toast("Message copié.")

        dialog.connect("response", on_response)
        dialog.present(self)

    def set_busy(self, busy, message=""):
        self.busy = busy
        self.clone_button.set_sensitive(not busy)
        self.banner.set_title(message)
        self.banner.set_revealed(busy)
        if busy:
            self.push_button.set_sensitive(False)
        else:
            self.progress.set_visible(False)
            self.update_action_button()
            if self.refresh_queued:
                self.refresh_queued = False
                GLib.idle_add(self.refresh, False)

    def set_progress(self, fraction, text):
        self.progress.set_visible(True)
        self.progress.set_fraction(fraction)
        self.banner.set_title(text)
        return GLib.SOURCE_REMOVE

    def _fill_group(self, group, rows, empty_row, items, description):
        """Remplit (ou vide) un groupe de préférences avec la liste des fichiers."""
        for row in rows:
            group.remove(row)
        rows.clear()
        group.set_description(description)
        empty_row.set_visible(not items)
        for code, path in items[:50]:
            label, icon = STATUS_LABELS.get(code, ("Modifié", "text-x-generic-symbolic"))
            row = Adw.ActionRow(title=GLib.markup_escape_text(path), subtitle=label)
            row.add_prefix(Gtk.Image(icon_name=icon))
            full_path = REPO_PATH / path
            if code != "D" and full_path.is_file():
                row.set_subtitle(f"{label} · {GLib.format_size(full_path.stat().st_size)}")
                row.set_activatable(True)
                row.add_suffix(
                    Gtk.Image(
                        icon_name="document-edit-symbolic", css_classes=["dim-label"]
                    )
                )
                row.connect("activated", self.on_open_file, full_path)
            group.add(row)
            rows.append(row)
        if len(items) > 50:
            row = Adw.ActionRow(title=f"… et {len(items) - 50} autres fichiers")
            group.add(row)
            rows.append(row)

    def refresh(self, check_remote=True):
        if self.busy:
            self.refresh_queued = True
            return GLib.SOURCE_REMOVE
        cloned = is_cloned()
        self.stack.set_visible_child_name("repo" if cloned else "welcome")
        self.push_button.set_visible(cloned)
        if not cloned:
            return GLib.SOURCE_REMOVE

        try:
            branch = current_branch()
            files = pending_changes()
        except GitError as error:
            self.show_error("Lecture du dépôt impossible", str(error))
            return GLib.SOURCE_REMOVE

        self.current_branch = branch
        self.pending_files = files
        self.operation = operation_in_progress()

        to_send = [c for c in files if c[0] != "D"]
        deleted = [c for c in files if c[0] == "D"]

        total, _big = upload_size(to_send)
        self._fill_group(
            self.changes_group,
            self.changes_rows,
            self.empty_row,
            to_send,
            f"{len(to_send)} fichier(s) · {GLib.format_size(total)} à envoyer"
            if to_send
            else None,
        )
        self._fill_group(
            self.deleted_group,
            self.deleted_rows,
            self.deleted_empty,
            deleted,
            f"{len(deleted)} fichier(s) supprimé(s)" if deleted else None,
        )

        self.update_action_button()
        if check_remote:
            self.check_remote(auto_pull=False)
        return GLib.SOURCE_REMOVE

    def update_action_button(self):
        """Derive the button's mode/label/sensitivity from local + remote state."""
        files, behind = self.pending_files, self.behind

        if self.operation:
            message = OPERATION_MESSAGES.get(self.operation, "Opération Git en cours")
            self.branch_row.set_subtitle(
                GLib.markup_escape_text(f"{self.current_branch or '—'} · {message}")
            )
            self.branch_row.add_css_class("warning")
            self.action_mode = "push"
            self.action_content.set_label("Push")
            self.push_button.set_tooltip_text(message)
            self.push_button.set_sensitive(False)
            return
        self.branch_row.remove_css_class("warning")

        text = self.current_branch or "—"
        if behind:
            text += f" · {behind} commit(s) en retard sur GitLab"
        if self.ahead:
            text += f" · {self.ahead} commit(s) pas encore envoyé(s)"
        self.branch_row.set_subtitle(GLib.markup_escape_text(text))

        if files and behind:
            self.action_mode = "sync"
            label = "Synchroniser"
            tooltip = (
                f"Envoyer {len(files)} fichier(s) et récupérer {behind} "
                "commit(s) depuis GitLab"
            )
        elif files or self.ahead:
            self.action_mode = "push"
            label = "Push"
            tooltip = f"Envoyer {len(files)} fichier(s) vers GitLab" if files else "Envoyer les commits en attente"
        elif behind:
            self.action_mode = "pull"
            label = "Pull"
            tooltip = f"Récupérer {behind} commit(s) depuis GitLab"
        else:
            self.action_mode = "push"
            label = "Push"
            tooltip = "Aucune modification à envoyer"

        self.action_content.set_label(label)
        self.push_button.set_tooltip_text(tooltip)
        self.push_button.set_sensitive(bool(files or behind or self.ahead) and not self.busy)

    def check_remote(self, auto_pull=False):
        """Fetch origin in the background and update the ahead/behind state.

        With auto_pull=True (app startup), also silently fast-forwards the
        local repo when GitLab is ahead, so edits made on the website are
        already merged in by the time the window is usable.
        """
        if not is_cloned() or self.busy:
            return
        # Rebasage/fusion interrompu : ne rien lancer, signaler l'état au lieu de
        # afficher « HEAD » et un compteur d'avance trompeur.
        self.operation = operation_in_progress()
        if self.operation:
            try:
                self.current_branch = current_branch()
            except GitError:
                pass
            self.ahead = self.behind = 0
            self.update_action_button()
            return
        self.set_busy(True, "Vérification de GitLab…")

        def work():
            fetch_remote()
            branch = current_branch()
            ahead, behind = ahead_behind(branch)
            pulled = 0
            if auto_pull and behind:
                before = run_git(["rev-parse", "HEAD"], cwd=REPO_PATH).strip()
                run_git(["pull", "--rebase", "--autostash"], cwd=REPO_PATH)
                after = run_git(["rev-parse", "HEAD"], cwd=REPO_PATH).strip()
                if after != before:
                    pulled = behind
                    ahead, behind = ahead_behind(branch)
            return ahead, behind, pulled

        def finished(result):
            pulled = 0
            if result is not None:
                self.ahead, self.behind, pulled = result
            self.set_busy(False)  # re-derives the button from the fresh state
            if pulled:
                self.toast(f"{pulled} commit(s) récupéré(s) depuis GitLab")
                self.refresh(check_remote=False)
            return GLib.SOURCE_REMOVE

        def wrapper():
            try:
                result = work()
            except GitError:
                result = None  # hors ligne ou non authentifié : on se tait
            GLib.idle_add(finished, result)

        threading.Thread(target=wrapper, daemon=True).start()

    def on_open_file(self, _row, path):
        Gtk.FileLauncher.new(Gio.File.new_for_path(str(path))).launch(
            self, None, None
        )

    def on_open_folder(self, _button):
        Gtk.FileLauncher.new(Gio.File.new_for_path(str(REPO_PATH))).launch(
            self, None, None
        )

    def run_task(self, func, busy_message):
        self.set_busy(True, busy_message)

        def finished(message, failed):
            self.set_busy(False)
            self.refresh()
            if not failed:
                self.toast(message)
            elif is_network_error(message):
                self.show_error(
                    "Connexion coupée pendant l’envoi",
                    "La connexion à GitLab a été interrompue (réseau instable ou envoi trop long). "
                    "Rien n’a été perdu : le commit non envoyé a été défait et tes fichiers sont "
                    "intacts dans le dossier. Supprime ou ignore les gros fichiers puis relance.\n\n" + message,
                )
            elif is_auth_error(message):
                self.toast("GitLab ne reconnaît pas cet ordinateur.")
                self.ask_connect(
                    "GitLab ne reconnaît pas encore cet ordinateur. "
                    "Suis les trois étapes ci-dessous une seule fois."
                )
            else:
                self.show_error("L’opération a échoué", message)
            return GLib.SOURCE_REMOVE

        def worker():
            try:
                message, failed = func(), False
            except Exception as error:  # noqa: BLE001
                message, failed = str(error), True
            GLib.idle_add(finished, message, failed)

        threading.Thread(target=worker, daemon=True).start()

    def ask_connect(self, description=None):
        try:
            public_key = ensure_ssh_key()
            use_ssh_remote()
        except (GitError, OSError) as error:
            self.show_error("Clé SSH indisponible", str(error))
            return

        dialog = Adw.AlertDialog(
            heading="Connexion à GitLab",
            body=description
            or "Trois étapes, une seule fois : copie la clé de cet "
            "ordinateur, colle-la sur GitLab, puis teste.",
        )

        group = Adw.PreferencesGroup()

        copy_row = Adw.ActionRow(
            title="1. Copier la clé de cet ordinateur",
            subtitle="Clé publique SSH, sans danger à partager",
        )
        copy_button = Gtk.Button(label="Copier", valign=Gtk.Align.CENTER)
        copy_button.add_css_class("suggested-action")

        def on_copy(_button):
            Gdk.Display.get_default().get_clipboard().set(public_key)
            copy_button.set_label("Copié")
            self.toast("Clé copiée. Colle-la sur GitLab (étape 2).")

        copy_button.connect("clicked", on_copy)
        copy_row.add_suffix(copy_button)
        group.add(copy_row)

        open_row = Adw.ActionRow(
            title="2. Coller sur GitLab",
            subtitle="Clé → « Add new key » → Coller → « Add key »",
        )
        open_button = Gtk.Button(label="Ouvrir GitLab", valign=Gtk.Align.CENTER)
        open_button.connect(
            "clicked",
            lambda *_: Gtk.UriLauncher.new(SSH_KEYS_URL).launch(self, None, None),
        )
        open_row.add_suffix(open_button)
        group.add(open_row)

        test_row = Adw.ActionRow(
            title="3. Tester la connexion",
            subtitle="Vérifie que GitLab accepte cet ordinateur",
        )
        test_button = Gtk.Button(label="Tester", valign=Gtk.Align.CENTER)

        def on_test(_button):
            test_button.set_sensitive(False)
            test_row.set_subtitle("Test en cours…")

            def finished(text):
                test_button.set_sensitive(True)
                test_row.set_subtitle(text)
                return GLib.SOURCE_REMOVE

            def worker():
                try:
                    run_command(["git", "ls-remote", REPO_SSH_URL])
                    text = "Connexion réussie, tu peux push."
                except GitError:
                    text = "Pas encore accepté : refais l’étape 2."
                GLib.idle_add(finished, text)

            threading.Thread(target=worker, daemon=True).start()

        test_button.connect("clicked", on_test)
        test_row.add_suffix(test_button)
        group.add(test_row)

        dialog.set_extra_child(group)
        dialog.add_response("close", "Fermer")
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.present(self)

    def ask_token(self, description=None):
        dialog = Adw.AlertDialog(
            heading="Jeton d’accès GitLab",
            body=description
            or "Le jeton est enregistré dans le trousseau GNOME et utilisé "
            "pour les opérations git sur gitlab.com.",
        )
        group = Adw.PreferencesGroup()
        entry = Adw.PasswordEntryRow(title="Jeton personnel")
        entry.set_text(load_token())
        group.add(entry)
        dialog.set_extra_child(group)

        dialog.add_response("cancel", "Annuler")
        dialog.add_response("save", "Enregistrer")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        def on_response(_dialog, response):
            if response != "save":
                return
            token = entry.get_text().strip()
            try:
                if token:
                    store_token(token)
                    self.toast("Jeton enregistré dans le trousseau.")
                else:
                    clear_token()
                    self.toast("Jeton supprimé.")
            except GLib.Error as error:
                self.toast(f"Trousseau indisponible : {error.message}")

        dialog.connect("response", on_response)
        dialog.present(self)

    # actions ---------------------------------------------------------------

    def on_clone_clicked(self, _button):
        def work():
            if is_cloned():
                return "Le dépôt est déjà cloné."
            clone_repo()
            return f"Dépôt cloné dans {REPO_PATH}"

        self.run_task(work, "Clonage en cours…")

    def ask_reclone(self):
        dialog = Adw.AlertDialog(
            heading="Recloner le dépôt ?",
            body=f"{REPO_PATH} part à la corbeille, puis une copie neuve de "
            "GitLab est téléchargée. Les modifications locales non envoyées "
            "ne seront plus dans le dossier.",
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("reclone", "Recloner")
        dialog.set_response_appearance(
            "reclone", Adw.ResponseAppearance.DESTRUCTIVE
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(_dialog, response):
            if response != "reclone":
                return

            def work():
                if REPO_PATH.exists():
                    trash_path(REPO_PATH)
                clone_repo()
                return f"Dépôt recloné dans {REPO_PATH}"

            self.run_task(work, "Reclonage en cours…")

        dialog.connect("response", on_response)
        dialog.present(self)

    def on_action_clicked(self, _button):
        if self.action_mode == "pull":
            self.run_task(self.do_pull, "Récupération depuis GitLab…")
            return
        self.refresh(check_remote=False)
        _total, big = upload_size(self.pending_files)
        if big:
            self.ask_big_files(big)
        else:
            self.start_push()

    def start_push(self):
        message = self.message_row.get_text().strip() or "Mise à jour"
        busy = "Synchronisation…" if self.action_mode == "sync" else "Envoi vers GitLab…"
        self.run_task(lambda: self.do_push(message), busy)

    def ask_big_files(self, big):
        listing = "\n".join(f"{GLib.format_size(size)}  {path}" for path, size, _code in big)
        untracked = [path for path, _size, code in big if code == "?"]
        dialog = Adw.AlertDialog(
            heading="Gros fichiers à envoyer",
            body="Sur une connexion fragile, un gros envoi risque d’être coupé. "
            "Les nouveaux fichiers peuvent rester dans le dossier en étant ignorés par Git "
            "(liste locale .git/info/exclude, rien n’est envoyé sur GitLab).",
        )
        view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, css_classes=["card"],
                            left_margin=10, right_margin=10, top_margin=8, bottom_margin=8)
        view.get_buffer().set_text(listing)
        dialog.set_extra_child(view)
        dialog.add_response("cancel", "Annuler")
        if untracked:
            dialog.add_response("exclude", "Ne pas envoyer les nouveaux")
        dialog.add_response("send", "Envoyer quand même")
        dialog.set_response_appearance("send", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("exclude" if untracked else "cancel")
        dialog.set_close_response("cancel")

        def on_response(_dialog, response):
            if response == "send":
                self.start_push()
            elif response == "exclude":
                exclude_paths(untracked)
                self.refresh(check_remote=False)
                if self.pending_files or self.ahead:
                    self.start_push()

        dialog.connect("response", on_response)
        dialog.present(self)

    def report_progress(self, fraction, text):
        GLib.idle_add(self.set_progress, fraction, text)

    def do_push(self, message):
        if not is_cloned():
            raise GitError("Clonez d’abord le dépôt.")
        operation = operation_in_progress()
        if operation:
            raise GitError(OPERATION_MESSAGES.get(operation, "Opération Git en cours"))
        branch = current_branch()
        fetch_remote()
        base = merge_base(branch)
        if base:
            # Regroupe les commits locaux non envoyés : un fichier supprimé depuis un envoi raté
            # ne reste plus dans l'historique à pousser.
            run_git(["reset", "--soft", base], cwd=REPO_PATH)
        run_git(["add", "--all"], cwd=REPO_PATH)
        if run_git(["diff", "--cached", "--name-only"], cwd=REPO_PATH):
            try:
                identity = run_git(
                    ["config", "--get", "user.email"], cwd=REPO_PATH
                ).strip()
            except GitError:
                identity = ""
            if not identity:
                run_git(["config", "user.email", GIT_EMAIL], cwd=REPO_PATH)
                run_git(["config", "user.name", GIT_NAME], cwd=REPO_PATH)
            run_git(["commit", "--message", message], cwd=REPO_PATH)
        try:
            run_git(["pull", "--rebase", "--autostash"], cwd=REPO_PATH)
        except GitError:
            if operation_in_progress() == "rebase":
                run_git(["rebase", "--abort"], cwd=REPO_PATH)
            self.undo_local_commits(branch)
            raise
        error = None
        for attempt in range(PUSH_ATTEMPTS):
            url = REPO_SSH_443_URL if attempt and SSH_KEY.exists() else "origin"
            try:
                run_git_progress(["push", "--progress", url, f"HEAD:refs/heads/{branch}"], self.report_progress)
                break
            except GitError as failure:
                error = failure
                if not is_network_error(str(failure)):
                    break
                self.report_progress(0, f"Connexion coupée, nouvel essai ({attempt + 2}/{PUSH_ATTEMPTS})…")
        if error is not None and not self.pushed(branch):
            self.undo_local_commits(branch)
            raise error
        run_git(["fetch", "--quiet", "origin"], cwd=REPO_PATH)
        return f"Fichiers envoyés vers origin/{branch}"

    def pushed(self, branch):
        try:
            fetch_remote()
        except GitError:
            return False
        return ahead_behind(branch)[0] == 0

    def undo_local_commits(self, branch):
        base = merge_base(branch)
        if base:
            run_git(["reset", "--mixed", "--quiet", base], cwd=REPO_PATH)

    def do_pull(self):
        if not is_cloned():
            raise GitError("Clonez d’abord le dépôt.")
        operation = operation_in_progress()
        if operation:
            raise GitError(OPERATION_MESSAGES.get(operation, "Opération Git en cours"))
        branch = current_branch()
        before = run_git(["rev-parse", "HEAD"], cwd=REPO_PATH).strip()
        run_git(["pull", "--rebase", "--autostash"], cwd=REPO_PATH)
        after = run_git(["rev-parse", "HEAD"], cwd=REPO_PATH).strip()
        if before == after:
            return "Déjà à jour."
        return f"Dépôt mis à jour depuis origin/{branch}"


class Application(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)
        connect_action = Gio.SimpleAction.new("connect", None)
        connect_action.connect(
            "activate", lambda *_: self.props.active_window.ask_connect()
        )
        self.add_action(connect_action)
        reclone_action = Gio.SimpleAction.new("reclone", None)
        reclone_action.connect(
            "activate", lambda *_: self.props.active_window.ask_reclone()
        )
        self.add_action(reclone_action)
        token_action = Gio.SimpleAction.new("token", None)
        token_action.connect(
            "activate", lambda *_: self.props.active_window.ask_token()
        )
        self.add_action(token_action)
        self.set_accels_for_action("window.close", ["<Primary>w", "<Primary>q"])

    def do_activate(self):
        window = self.props.active_window or Window(application=self)
        window.present()

    def on_about(self, *_args):
        about = Adw.AboutDialog(
            application_name="Pusher",
            application_icon=APP_ID,
            version=VERSION,
            developer_name="Shogu",
            license_type=Gtk.License.GPL_3_0,
            website=REPO_URL.removesuffix(".git"),
            comments=f"Cloner {REPO_NAME} dans ~/Gitlab et le garder "
            "synchronisé avec GitLab, dans les deux sens.",
        )
        about.present(self.props.active_window)


def main():
    ctypes.CDLL(None).prctl(15, b"pusher", 0, 0, 0)
    GLib.set_application_name("Pusher")
    return Application().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
