# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialogues : pochette en ligne, doublons, aperçu de renommage."""

from __future__ import annotations

import os
import threading

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

from . import covers, duplicates
from .model import texture_from_bytes


def _spinner():
    spinner = Adw.Spinner()
    spinner.set_size_request(32, 32)
    spinner.set_halign(Gtk.Align.CENTER)
    return spinner


def _status(icon: str, title: str, description: str = "") -> Adw.StatusPage:
    return Adw.StatusPage(icon_name=icon, title=title, description=description)


# ---------------------------------------------------------------------------
# Pochette en ligne
# ---------------------------------------------------------------------------

class CoverSearchDialog(Adw.Dialog):
    __gtype_name__ = "DisquaireCoverSearchDialog"

    def __init__(self, query: str, on_chosen):
        super().__init__(title="Pochette en ligne", content_width=760, content_height=620)
        self._on_chosen = on_chosen
        self._generation = 0
        self._count = 0

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        bar = Gtk.Box(spacing=8, margin_start=12, margin_end=12, margin_bottom=8)
        self.entry = Gtk.SearchEntry(text=query, hexpand=True,
                                     placeholder_text="Artiste et album")
        self.entry.connect("activate", lambda *_: self.search())
        go = Gtk.Button(label="Rechercher")
        go.add_css_class("suggested-action")
        go.connect("clicked", lambda *_: self.search())
        bar.append(self.entry)
        bar.append(go)
        toolbar.add_top_bar(bar)

        self.flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
            min_children_per_line=2, max_children_per_line=4,
            column_spacing=12, row_spacing=12,
            margin_top=12, margin_bottom=24, margin_start=12, margin_end=12,
            valign=Gtk.Align.START,
        )
        scrolled = Gtk.ScrolledWindow(child=self.flow,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)

        searching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                            valign=Gtk.Align.CENTER)
        searching.append(_spinner())
        label = Gtk.Label(label="Recherche d'images d'au moins 1024 × 1024…")
        label.add_css_class("dim-label")
        searching.append(label)
        self.status_label = Gtk.Label(label="", wrap=True)
        self.status_label.add_css_class("caption")
        self.status_label.add_css_class("dim-label")
        searching.append(self.status_label)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(scrolled, "results")
        self.stack.add_named(searching, "searching")
        self.none_page = _status("image-missing-symbolic", "Aucune pochette en grand format",
                                 "Aucune image d'au moins 1024 px n'a été trouvée. "
                                 "Essayez une autre recherche.")
        self.stack.add_named(self.none_page, "none")
        toolbar.set_content(self.stack)

        self.more = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_UP)
        more_box = Gtk.Box(spacing=8, margin_top=6, margin_bottom=6,
                           halign=Gtk.Align.CENTER)
        more_box.append(_spinner())
        self.more_label = Gtk.Label(label="Recherche en cours…")
        self.more_label.add_css_class("caption")
        more_box.append(self.more_label)
        self.more.set_child(more_box)
        toolbar.add_bottom_bar(self.more)

        self.set_child(toolbar)
        self.connect("closed", lambda *_: self._stop())
        if query.strip():
            GLib.idle_add(self._start_once)

    def _start_once(self):
        self.search()
        return GLib.SOURCE_REMOVE

    def _stop(self):
        self._generation += 1

    def search(self):
        query = self.entry.get_text().strip()
        if not query:
            return
        self._generation += 1
        gen = self._generation
        self._count = 0
        child = self.flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.flow.remove(child)
            child = nxt
        self.stack.set_visible_child_name("searching")

        self.status_label.set_label("")
        self._statuses = []

        def status(text):
            GLib.idle_add(self._status, gen, text)

        def work():
            errors = []
            try:
                errors = covers.search(
                    query,
                    on_result=lambda c: GLib.idle_add(self._add, gen, c),
                    should_stop=lambda: gen != self._generation,
                    on_status=status,
                )
            except Exception as exc:  # jamais de recherche qui tourne sans fin
                errors = [str(exc)]
            finally:
                GLib.idle_add(self._finish, gen, errors)

        threading.Thread(target=work, daemon=True).start()

    def _status(self, gen, text):
        if gen == self._generation:
            self._statuses.append(text)
            joined = " · ".join(self._statuses)
            self.status_label.set_label(joined)
            self.more_label.set_label("Téléchargement des images… " + joined)
        return GLib.SOURCE_REMOVE

    def _add(self, gen, cand: covers.Candidate):
        if gen != self._generation:
            return GLib.SOURCE_REMOVE
        texture = texture_from_bytes(cand.data)
        if texture is None:
            return GLib.SOURCE_REMOVE
        self._count += 1
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        picture = Gtk.Picture(paintable=texture, content_fit=Gtk.ContentFit.COVER,
                              can_shrink=True)
        picture.set_size_request(150, 150)
        picture.set_overflow(Gtk.Overflow.HIDDEN)
        picture.add_css_class("thumb")
        size = Gtk.Label(label=f"{cand.width} × {cand.height} · {cand.source}")
        size.add_css_class("caption-heading")
        name = Gtk.Label(label=cand.label, ellipsize=Pango.EllipsizeMode.END,
                         max_width_chars=22)
        name.add_css_class("caption")
        name.add_css_class("dim-label")
        box.append(picture)
        box.append(size)
        box.append(name)
        button = Gtk.Button(child=box, tooltip_text=cand.label)
        button.add_css_class("flat")
        button.connect("clicked", lambda *_: self._choose(cand))
        self.flow.append(button)
        self.stack.set_visible_child_name("results")
        self.more.set_reveal_child(True)
        return GLib.SOURCE_REMOVE

    def _finish(self, gen, errors):
        if gen != self._generation:
            return GLib.SOURCE_REMOVE
        self.more.set_reveal_child(False)
        if self._count == 0:
            self.none_page.set_title("Aucune pochette en grand format")
            self.none_page.set_description(
                "Aucune image d'au moins 1024 px n'a été trouvée. "
                "Essayez une autre recherche (artiste et album).")
            if errors and not any("album" in s and not s.endswith(": 0 album(s)")
                                  for s in self._statuses):
                self.none_page.set_title("Recherche impossible")
                self.none_page.set_description(GLib.markup_escape_text(
                    "Vérifiez la connexion à Internet.\n" + "\n".join(errors)))
            self.stack.set_visible_child_name("none")
        return GLib.SOURCE_REMOVE

    def _choose(self, cand):
        self._stop()
        self.close()
        self._on_chosen(cand.data)


# ---------------------------------------------------------------------------
# Doublons
# ---------------------------------------------------------------------------

class DuplicatesDialog(Adw.Dialog):
    __gtype_name__ = "DisquaireDuplicatesDialog"

    def __init__(self, root: str, on_trashed, on_open):
        super().__init__(title="Doublons", content_width=820, content_height=680)
        self.root = root
        self._on_trashed = on_trashed
        self._on_open = on_open
        self._stop = threading.Event()
        self._groups: list[dict] = []

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.rescan = Gtk.Button(icon_name="view-refresh-symbolic",
                                 tooltip_text="Relancer la recherche")
        self.rescan.connect("clicked", lambda *_: self.scan())
        header.pack_start(self.rescan)
        toolbar.add_top_bar(header)

        scanning = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                           valign=Gtk.Align.CENTER, margin_start=48, margin_end=48)
        scanning.append(_spinner())
        self.scan_label = Gtk.Label(label="Lecture de la discothèque…")
        scanning.append(self.scan_label)
        self.scan_bar = Gtk.ProgressBar()
        scanning.append(self.scan_bar)
        root_label = Gtk.Label(label=root, ellipsize=Pango.EllipsizeMode.MIDDLE)
        root_label.add_css_class("caption")
        root_label.add_css_class("dim-label")
        scanning.append(root_label)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                                margin_top=12, margin_bottom=24)
        intro = Gtk.Label(
            label="Recherche floue : les morceaux aux noms proches et de même durée "
                  "(à 4 s près) sont regroupés. Les fichiers cochés partiront à la "
                  "corbeille ; l'exemplaire à garder (MP3 320, sinon FLAC, sinon le "
                  "meilleur débit) est décoché d'office.",
            wrap=True, xalign=0, margin_bottom=6)
        intro.add_css_class("dim-label")
        self.list_box.append(intro)
        clamp = Adw.Clamp(child=self.list_box, maximum_size=760,
                          margin_start=12, margin_end=12)
        scrolled = Gtk.ScrolledWindow(child=clamp, hscrollbar_policy=Gtk.PolicyType.NEVER)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(scanning, "scanning")
        self.stack.add_named(scrolled, "results")
        self.stack.add_named(_status("disquaire-ok-symbolic", "Aucun doublon",
                                     "Chaque morceau n'est présent qu'une fois."), "none")
        toolbar.set_content(self.stack)

        self.action_bar = Gtk.ActionBar(revealed=False)
        self.summary = Gtk.Label()
        self.summary.add_css_class("heading")
        self.action_bar.pack_start(self.summary)
        self.trash_button = Gtk.Button(label="Mettre à la corbeille")
        self.trash_button.add_css_class("destructive-action")
        self.trash_button.connect("clicked", lambda *_: self._confirm_trash())
        self.action_bar.pack_end(self.trash_button)
        toolbar.add_bottom_bar(self.action_bar)

        self.toasts = Adw.ToastOverlay(child=toolbar)
        self.set_child(self.toasts)
        self.connect("closed", lambda *_: self._stop.set())
        GLib.idle_add(lambda: (self.scan(), False)[1])

    # --- recherche ----------------------------------------------------
    def scan(self):
        self._stop.set()
        self._stop = threading.Event()
        stop = self._stop
        self.stack.set_visible_child_name("scanning")
        self.action_bar.set_revealed(False)
        self.rescan.set_sensitive(False)
        self.scan_bar.set_fraction(0)

        def progress(i, n):
            GLib.idle_add(self._progress, i, n)

        def work():
            groups = duplicates.find(self.root, progress, stop.is_set)
            if not stop.is_set():
                GLib.idle_add(self._show, groups)

        threading.Thread(target=work, daemon=True).start()

    def _progress(self, i, n):
        self.scan_label.set_label(f"Lecture de la discothèque… {i} / {n}")
        self.scan_bar.set_fraction(i / n if n else 0)
        return GLib.SOURCE_REMOVE

    def _show(self, groups):
        self.rescan.set_sensitive(True)
        for g in self._groups:
            self.list_box.remove(g["widget"])
        self._groups = []
        if not groups:
            self.stack.set_visible_child_name("none")
            return GLib.SOURCE_REMOVE
        for files in groups:
            self._add_group(files)
        self.stack.set_visible_child_name("results")
        self._update()
        return GLib.SOURCE_REMOVE

    def _add_group(self, files):
        best = files[0]
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=12)
        artist = best.artist or "Artiste inconnu"
        title = best.title or os.path.splitext(os.path.basename(best.path))[0]
        heading = Gtk.Label(label=f"{artist} — {title}", xalign=0, wrap=True)
        heading.add_css_class("heading")
        fuzzy = "" if duplicates.exact_names(files) else " · noms différents"
        count = Gtk.Label(label=f"{len(files)} exemplaires{fuzzy}", xalign=0)
        count.add_css_class("caption")
        count.add_css_class("dim-label")
        listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        box.append(heading)
        box.append(count)
        box.append(listbox)
        group = {"widget": box, "listbox": listbox, "rows": [], "count": count,
                 "fuzzy": fuzzy}
        for f in files:
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(os.path.basename(f.path)),
                subtitle=GLib.markup_escape_text(
                    f"Tags : {f.artist or '?'} — {f.title or '?'}\n"
                    f"{self._rel(os.path.dirname(f.path))}\n{f.describe()}"),
            )
            row.set_subtitle_lines(3)
            check = Gtk.CheckButton(valign=Gtk.Align.CENTER, active=f is not best)
            check.add_css_class("selection-mode")
            check.connect("toggled", lambda *_: self._update())
            row.add_prefix(check)
            row.set_activatable_widget(check)
            if f is best:
                keep = Gtk.Label(label="À garder", valign=Gtk.Align.CENTER)
                keep.add_css_class("keep-badge")
                row.add_suffix(keep)
            open_btn = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER,
                                  tooltip_text="Ouvrir dans Disquaire")
            open_btn.add_css_class("flat")
            open_btn.connect("clicked", lambda _b, p=f.path: self._open(p))
            row.add_suffix(open_btn)
            listbox.append(row)
            group["rows"].append((row, check, f))
        self.list_box.append(box)
        self._groups.append(group)

    def _rel(self, folder):
        try:
            rel = os.path.relpath(folder, self.root)
        except ValueError:
            return folder
        return "Dossier de base" if rel == "." else rel

    def _checked(self):
        return [(g, row, f) for g in self._groups for row, check, f in g["rows"]
                if check.get_active()]

    def _update(self):
        checked = self._checked()
        size = sum(f.size for _g, _r, f in checked)
        self.summary.set_label(
            f"{len(checked)} fichier{'s' if len(checked) > 1 else ''} · "
            f"{duplicates.human_size(size)}" if checked else
            f"{len(self._groups)} groupe{'s' if len(self._groups) > 1 else ''} de doublons")
        self.trash_button.set_sensitive(bool(checked))
        self.action_bar.set_revealed(bool(self._groups))

    def _open(self, path):
        self._stop.set()
        self.close()
        self._on_open(path)

    # --- corbeille ----------------------------------------------------
    def _confirm_trash(self):
        whole = [g for g in self._groups if all(c.get_active() for _r, c, _f in g["rows"])]
        if not whole:
            self._trash()
            return
        dialog = Adw.AlertDialog(
            heading="Supprimer tous les exemplaires ?",
            body=f"Dans {len(whole)} groupe(s), tous les fichiers sont cochés : "
                 "le morceau disparaîtra complètement de la discothèque.",
        )
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("trash", "Tout mettre à la corbeille")
        dialog.set_response_appearance("trash", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _d, r: self._trash() if r == "trash" else None)
        dialog.present(self)

    def _trash(self):
        trashed, errors = [], []
        for g, row, f in self._checked():
            try:
                Gio.File.new_for_path(f.path).trash(None)
            except GLib.Error as exc:
                errors.append(f"{os.path.basename(f.path)} : {exc.message}")
                continue
            trashed.append(f.path)
            g["listbox"].remove(row)
            g["rows"] = [r for r in g["rows"] if r[0] is not row]
        for g in list(self._groups):
            if len(g["rows"]) <= 1:
                self.list_box.remove(g["widget"])
                self._groups.remove(g)
            else:
                g["count"].set_label(f"{len(g['rows'])} exemplaires{g['fuzzy']}")
        self._update()
        if not self._groups:
            self.stack.set_visible_child_name("none")
        if trashed:
            self._on_trashed(trashed)
            self.toasts.add_toast(Adw.Toast(
                title=f"{len(trashed)} fichier(s) mis à la corbeille", timeout=3))
        if errors:
            alert = Adw.AlertDialog(heading="Certains fichiers n'ont pas pu être supprimés",
                                    body="\n".join(errors))
            alert.add_response("ok", "OK")
            alert.present(self)


# ---------------------------------------------------------------------------
# Aperçu de renommage
# ---------------------------------------------------------------------------

def rename_preview(parent, plan, skipped, on_confirm, heading=None, note="",
                  item_label="fichier", skipped_reason=None, confirm_label=None) -> None:
    """`plan` : liste de (ancien nom, nouveau nom)."""
    n = len(plan)
    lines = [note] if note else []
    if item_label == "fichier":
        summary = (f"{n} fichier{'s' if n > 1 else ''} à renommer en "
                   "« Artiste - Titre Feat. Invité ».")
    else:
        summary = f"{n} {item_label}{'s' if n > 1 else ''} à renommer."
    lines.append(summary if n else f"Aucun {item_label} à renommer.")
    if skipped:
        reason = skipped_reason or "artiste ou titre introuvable"
        lines.append(f"{len(skipped)} {item_label}(s) ignoré(s) : {reason}.")
    dialog = Adw.AlertDialog(
        heading=heading or f"Renommer {n} fichier{'s' if n > 1 else ''} ?",
        body="\n".join(lines),
    )
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                  margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
    for old, new in plan:
        line = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        o = Gtk.Label(label=old, xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE)
        o.add_css_class("caption")
        o.add_css_class("dim-label")
        nw = Gtk.Label(label="→ " + new, xalign=0, wrap=True,
                       wrap_mode=Pango.WrapMode.WORD_CHAR)
        line.append(o)
        line.append(nw)
        box.append(line)
    scrolled = Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                  min_content_height=min(60 * n, 280),
                                  max_content_height=320, propagate_natural_height=True)
    if plan:
        dialog.set_extra_child(Gtk.Frame(child=scrolled))
    dialog.add_response("cancel", "Annuler")
    dialog.add_response("rename", confirm_label or ("Mettre en forme" if note else "Renommer"))
    dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("rename")
    dialog.set_close_response("cancel")
    dialog.connect("response", lambda _d, r: on_confirm() if r == "rename" else None)
    dialog.present(parent)


# ---------------------------------------------------------------------------
# Réserve de pochettes
# ---------------------------------------------------------------------------

def ask_name(parent, heading: str, initial: str, on_ok, ok_label="Enregistrer") -> None:
    dialog = Adw.AlertDialog(heading=heading)
    entry = Gtk.Entry(text=initial, activates_default=True,
                      placeholder_text="Genre (ex. : Jazz, Reggae, Électro)")
    dialog.set_extra_child(entry)
    dialog.add_response("cancel", "Annuler")
    dialog.add_response("ok", ok_label)
    dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("ok")
    dialog.set_close_response("cancel")
    dialog.connect("response", lambda _d, r: on_ok(entry.get_text()) if r == "ok" else None)
    dialog.present(parent)
    GLib.idle_add(lambda: (entry.grab_focus(), False)[1])


class ReserveDialog(Adw.Dialog):
    """Grille des pochettes de la réserve : un clic applique la pochette."""

    __gtype_name__ = "DisquaireReserveDialog"

    def __init__(self, current_cover, default_name: str, n_targets: int, on_chosen):
        super().__init__(title="Réserve de pochettes", content_width=720, content_height=600)
        from . import reserve
        self._reserve = reserve
        self._current = current_cover
        self._default = default_name
        self._on_chosen = on_chosen

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        add_menu = Gio.Menu()
        if current_cover is not None:
            add_menu.append("La pochette affichée…", "reserve.add-current")
        add_menu.append("Une image du disque…", "reserve.add-file")
        add_btn = Gtk.MenuButton(icon_name="list-add-symbolic", menu_model=add_menu,
                                 tooltip_text="Ajouter une pochette à la réserve")
        header.pack_start(add_btn)
        toolbar.add_top_bar(header)

        group = Gio.SimpleActionGroup()
        for name, cb in (("add-current", lambda *_: self._add_current()),
                         ("add-file", lambda *_: self._add_file())):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", cb)
            group.add_action(act)
        for name, cb in (("rename", self._rename), ("remove", self._remove)):
            act = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
            act.connect("activate", lambda _a, p, cb=cb: cb(p.get_string()))
            group.add_action(act)
        self.insert_action_group("reserve", group)

        hint = Gtk.Label(
            label=("Cliquez une pochette pour l'appliquer "
                   + ("au morceau sélectionné." if n_targets == 1 else
                      f"aux {n_targets} morceaux sélectionnés.")
                   + " Clic droit : renommer ou supprimer. Le nom sert à la suggestion "
                     "automatique d'après le genre."),
            wrap=True, xalign=0, margin_start=12, margin_end=12, margin_top=6)
        hint.add_css_class("dim-label")
        self.flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
            min_children_per_line=2, max_children_per_line=5,
            column_spacing=12, row_spacing=12, valign=Gtk.Align.START,
            margin_top=12, margin_bottom=24, margin_start=12, margin_end=12)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(hint)
        box.append(self.flow)
        scrolled = Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER)

        empty = Adw.StatusPage(
            icon_name="disquaire-reserve-symbolic", title="Réserve vide",
            description="Ajoutez la pochette affichée ou une image avec le bouton +. "
                        "Nommez-la d'après un genre pour qu'elle soit proposée "
                        "automatiquement aux morceaux sans pochette de ce genre.")
        self.stack = Gtk.Stack()
        self.stack.add_named(scrolled, "grid")
        self.stack.add_named(empty, "empty")
        toolbar.set_content(self.stack)
        self.toasts = Adw.ToastOverlay(child=toolbar)
        self.set_child(self.toasts)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop)
        self.toasts.add_controller(drop)
        self.refresh()

    # --- grille -------------------------------------------------------
    def refresh(self):
        child = self.flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.flow.remove(child)
            child = nxt
        items = self._reserve.entries()
        for name, path in items:
            self.flow.append(self._tile(name, path))
        self.stack.set_visible_child_name("grid" if items else "empty")

    def _tile(self, name, path):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        cover = self._reserve.load(path)
        picture = Gtk.Picture(paintable=texture_from_bytes(cover.data) if cover else None,
                              content_fit=Gtk.ContentFit.COVER, can_shrink=True)
        picture.set_size_request(120, 120)
        picture.set_overflow(Gtk.Overflow.HIDDEN)
        picture.add_css_class("thumb")
        label = Gtk.Label(label=name, ellipsize=Pango.EllipsizeMode.END, max_width_chars=16)
        label.add_css_class("heading")
        box.append(picture)
        box.append(label)
        button = Gtk.Button(child=box, tooltip_text=name)
        button.add_css_class("flat")
        button.connect("clicked", lambda *_: self._choose(path))
        click = Gtk.GestureClick(button=3)
        click.connect("pressed", lambda g, _n, x, y: self._menu(button, path, x, y))
        button.add_controller(click)
        return button

    def _menu(self, widget, path, x, y):
        menu = Gio.Menu()
        for label, action in (("Renommer…", "reserve.rename"), ("Supprimer", "reserve.remove")):
            item = Gio.MenuItem.new(label, None)
            item.set_action_and_target_value(action, GLib.Variant("s", path))
            menu.append_item(item)
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(widget)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        popover.set_pointing_to(rect)
        popover.connect("closed", lambda p: GLib.idle_add(p.unparent))
        popover.popup()

    def _choose(self, path):
        cover = self._reserve.load(path)
        if cover is None:
            self.toasts.add_toast(Adw.Toast(title="Image illisible"))
            return
        self.close()
        self._on_chosen(cover, os.path.splitext(os.path.basename(path))[0])

    # --- gestion ------------------------------------------------------
    def _store(self, name, cover):
        name = self._reserve.clean_name(name)
        if not name:
            return

        def write():
            try:
                self._reserve.add(name, cover)
            except (OSError, covers.CoverError) as exc:
                self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(str(exc))))
                return
            self.refresh()
            self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(
                f"« {name} » ajoutée à la réserve"), timeout=2))

        if os.path.exists(self._reserve.path_for(name)):
            alert = Adw.AlertDialog(heading=f"Remplacer « {name} » ?",
                                    body="Une pochette de la réserve porte déjà ce nom.")
            alert.add_response("cancel", "Annuler")
            alert.add_response("replace", "Remplacer")
            alert.set_response_appearance("replace", Adw.ResponseAppearance.DESTRUCTIVE)
            alert.set_close_response("cancel")
            alert.connect("response", lambda _d, r: write() if r == "replace" else None)
            alert.present(self)
        else:
            write()

    def _add_current(self):
        if self._current is not None:
            ask_name(self, "Ajouter à la réserve", self._default,
                     lambda name: self._store(name, self._current), "Ajouter")

    def _add_file(self):
        images = Gtk.FileFilter(name="Images")
        images.add_mime_type("image/*")
        filters = Gio.ListStore(item_type=Gtk.FileFilter)
        filters.append(images)
        dialog = Gtk.FileDialog(title="Image pour la réserve", filters=filters)

        def done(dlg, result):
            try:
                file = dlg.open_finish(result)
            except GLib.Error:
                return
            self._add_from_file(file)

        dialog.open(self.get_root(), None, done)

    def _add_from_file(self, file):
        try:
            ok, data, _etag = file.load_contents(None)
            cover = covers.prepare(bytes(data))
        except (GLib.Error, covers.CoverError) as exc:
            self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(str(exc))))
            return
        stem = os.path.splitext(file.get_basename() or "")[0]
        ask_name(self, "Ajouter à la réserve", self._default or stem,
                 lambda name: self._store(name, cover), "Ajouter")

    def _on_drop(self, _target, value, _x, _y):
        files = value.get_files()
        if files:
            self._add_from_file(files[0])
            return True
        return False

    def _rename(self, path):
        old = os.path.splitext(os.path.basename(path))[0]

        def do(name):
            try:
                self._reserve.rename(path, name)
            except (OSError, covers.CoverError) as exc:
                self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(str(exc))))
                return
            self.refresh()

        ask_name(self, "Renommer la pochette", old, do, "Renommer")

    def _remove(self, path):
        self._reserve.remove(path)
        self.refresh()
        self.toasts.add_toast(Adw.Toast(title="Pochette retirée de la réserve", timeout=2))


# ---------------------------------------------------------------------------
# Paroles en ligne
# ---------------------------------------------------------------------------

class LyricsDialog(Adw.Dialog):
    """Paroles trouvées en ligne : aperçu, puis « Utiliser ces paroles »."""

    __gtype_name__ = "DisquaireLyricsDialog"

    def __init__(self, artist, title, album, duration, on_chosen):
        super().__init__(title="Paroles en ligne", content_width=860, content_height=640)
        self._on_chosen = on_chosen
        self._duration = duration
        self._album = album
        self._gen = 0
        self._chosen = None

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.use_button = Gtk.Button(label="Utiliser ces paroles", sensitive=False)
        self.use_button.add_css_class("suggested-action")
        self.use_button.connect("clicked", lambda *_: self._use())
        header.pack_end(self.use_button)
        toolbar.add_top_bar(header)

        bar = Gtk.Box(spacing=8, margin_start=12, margin_end=12, margin_bottom=8)
        self.artist_entry = Gtk.Entry(text=artist, placeholder_text="Artiste", hexpand=True)
        self.title_entry = Gtk.Entry(text=title, placeholder_text="Titre", hexpand=True)
        for e in (self.artist_entry, self.title_entry):
            e.connect("activate", lambda *_: self.search())
        go = Gtk.Button(label="Rechercher")
        go.connect("clicked", lambda *_: self.search())
        bar.append(self.artist_entry)
        bar.append(self.title_entry)
        bar.append(go)
        toolbar.add_top_bar(bar)

        self.results = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.results.add_css_class("navigation-sidebar")
        self.results.connect("row-selected", self._on_selected)
        left = Gtk.ScrolledWindow(child=self.results, hscrollbar_policy=Gtk.PolicyType.NEVER)
        left.set_size_request(280, -1)

        self.preview = Gtk.TextView(editable=False, cursor_visible=False,
                                    wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                    top_margin=16, bottom_margin=16,
                                    left_margin=18, right_margin=18)
        self.preview.add_css_class("lyrics")
        right = Gtk.ScrolledWindow(child=self.preview, hexpand=True)

        paned = Gtk.Paned(start_child=left, end_child=right, position=300,
                          shrink_start_child=False, shrink_end_child=False)

        searching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                            valign=Gtk.Align.CENTER)
        searching.append(_spinner())
        lbl = Gtk.Label(label="Recherche des paroles…")
        lbl.add_css_class("dim-label")
        searching.append(lbl)
        self.none_page = _status("disquaire-music-symbolic",
                                 "Aucune parole correspondante trouvée",
                                 "Vérifiez l'artiste et le titre, puis relancez.")
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(paned, "results")
        self.stack.add_named(searching, "searching")
        self.stack.add_named(self.none_page, "none")
        toolbar.set_content(self.stack)
        self.set_child(toolbar)
        self.connect("closed", lambda *_: setattr(self, "_gen", self._gen + 1))
        GLib.idle_add(lambda: (self.search(), False)[1])

    def search(self):
        from . import lyrics
        artist = self.artist_entry.get_text().strip()
        title = self.title_entry.get_text().strip()
        if not title:
            return
        self._gen += 1
        gen = self._gen
        self.use_button.set_sensitive(False)
        self.stack.set_visible_child_name("searching")

        def work():
            try:
                found, error = lyrics.search(artist, title, self._album, self._duration), None
            except lyrics.LyricsError as exc:
                found, error = [], str(exc)
            GLib.idle_add(self._show, gen, found, error)

        threading.Thread(target=work, daemon=True).start()

    def _show(self, gen, found, error):
        if gen != self._gen:
            return GLib.SOURCE_REMOVE
        child = self.results.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.results.remove(child)
            child = nxt
        if not found:
            if error:
                self.none_page.set_title("Recherche impossible")
                self.none_page.set_description(GLib.markup_escape_text(
                    f"{error[0].upper()}{error[1:]}. Vérifiez la connexion à Internet."))
            else:
                self.none_page.set_title("Aucune parole correspondante trouvée")
                self.none_page.set_description("Vérifiez l'artiste et le titre, puis relancez.")
            self.stack.set_visible_child_name("none")
            return GLib.SOURCE_REMOVE
        from .tags import format_duration
        for c in found:
            details = [c.album] if c.album else []
            if c.duration:
                details.append(format_duration(c.duration))
            row = Adw.ActionRow(title=GLib.markup_escape_text(c.title),
                                subtitle=GLib.markup_escape_text(
                                    c.artist + ("\n" + " · ".join(details) if details else "")))
            row.set_subtitle_lines(2)
            if c.exact:
                badge = Gtk.Label(label="Conforme", valign=Gtk.Align.CENTER,
                                  tooltip_text="Même artiste, même titre, même durée")
                badge.add_css_class("keep-badge")
                row.add_suffix(badge)
            row.candidate = c
            self.results.append(row)
        self.stack.set_visible_child_name("results")
        self.results.select_row(self.results.get_row_at_index(0))
        return GLib.SOURCE_REMOVE

    def _on_selected(self, _box, row):
        self._chosen = getattr(row, "candidate", None) if row else None
        self.preview.get_buffer().set_text(self._chosen.text if self._chosen else "")
        self.use_button.set_sensitive(self._chosen is not None)

    def _use(self):
        if self._chosen is not None:
            text = self._chosen.text
            self._gen += 1
            self.close()
            self._on_chosen(text)


# ---------------------------------------------------------------------------
# Année et album en ligne
# ---------------------------------------------------------------------------

class ReleaseDialog(Adw.Dialog):
    """Sorties d'un morceau ; rien n'est appliqué sans un clic."""

    __gtype_name__ = "DisquaireReleaseDialog"

    def __init__(self, artist, title, on_apply):
        super().__init__(title="Année et album", content_width=640, content_height=620)
        self._on_apply = on_apply
        self._gen = 0

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        bar = Gtk.Box(spacing=8, margin_start=12, margin_end=12, margin_bottom=8)
        self.artist_entry = Gtk.Entry(text=artist, placeholder_text="Artiste", hexpand=True)
        self.title_entry = Gtk.Entry(text=title, placeholder_text="Titre", hexpand=True)
        for e in (self.artist_entry, self.title_entry):
            e.connect("activate", lambda *_: self.search())
        go = Gtk.Button(label="Rechercher")
        go.connect("clicked", lambda *_: self.search())
        bar.append(self.artist_entry)
        bar.append(self.title_entry)
        bar.append(go)
        toolbar.add_top_bar(bar)

        self.results = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.results.add_css_class("boxed-list")
        hint = Gtk.Label(
            label="La sortie la plus ancienne du morceau est en tête : c'est en général "
                  "l'année d'origine. Rien n'est modifié sans clic sur un bouton.",
            wrap=True, xalign=0)
        hint.add_css_class("dim-label")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=6, margin_bottom=24, margin_start=12, margin_end=12)
        box.append(hint)
        box.append(self.results)
        scrolled = Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER)

        searching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                            valign=Gtk.Align.CENTER)
        searching.append(_spinner())
        lbl = Gtk.Label(label="Recherche sur MusicBrainz et iTunes…")
        lbl.add_css_class("dim-label")
        searching.append(lbl)
        self.none_page = _status("disquaire-music-symbolic", "Aucune sortie trouvée",
                                 "Vérifiez l'artiste et le titre, puis relancez.")
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(scrolled, "results")
        self.stack.add_named(searching, "searching")
        self.stack.add_named(self.none_page, "none")
        toolbar.set_content(self.stack)
        self.set_child(toolbar)
        self.connect("closed", lambda *_: setattr(self, "_gen", self._gen + 1))
        GLib.idle_add(lambda: (self.search(), False)[1])

    def search(self):
        from . import releases
        artist = self.artist_entry.get_text().strip()
        title = self.title_entry.get_text().strip()
        if not title:
            return
        self._gen += 1
        gen = self._gen
        self.stack.set_visible_child_name("searching")

        def work():
            try:
                found, error = releases.search(artist, title), None
            except releases.ReleaseError as exc:
                found, error = [], str(exc)
            GLib.idle_add(self._show, gen, found, error)

        threading.Thread(target=work, daemon=True).start()

    def _show(self, gen, found, error):
        if gen != self._gen:
            return GLib.SOURCE_REMOVE
        child = self.results.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.results.remove(child)
            child = nxt
        if not found:
            if error:
                self.none_page.set_title("Recherche impossible")
                self.none_page.set_description(GLib.markup_escape_text(
                    f"{error[0].upper()}{error[1:]}. Vérifiez la connexion à Internet."))
            self.stack.set_visible_child_name("none")
            return GLib.SOURCE_REMOVE
        for r in found:
            sub = " · ".join(x for x in (r.kind_label(), r.artist, r.source) if x)
            row = Adw.ActionRow(title=GLib.markup_escape_text(f"{r.year} — {r.album}"),
                                subtitle=GLib.markup_escape_text(sub))
            if r.match:
                badge = Gtk.Label(label="Conforme", valign=Gtk.Align.CENTER)
                badge.add_css_class("keep-badge")
                row.add_suffix(badge)
            box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
            box.add_css_class("linked")
            for label, year, album in (("Année", r.year, None), ("Album", None, r.album),
                                       ("Les deux", r.year, r.album)):
                b = Gtk.Button(label=label)
                b.connect("clicked", lambda _b, y=year, a=album: self._apply(y, a))
                box.append(b)
            row.add_suffix(box)
            self.results.append(row)
        self.stack.set_visible_child_name("results")
        return GLib.SOURCE_REMOVE

    def _apply(self, year, album):
        self._gen += 1
        self.close()
        self._on_apply(year, album)


# ---------------------------------------------------------------------------
# Genres : liste proposée et genres de la discothèque
# ---------------------------------------------------------------------------

class GenresDialog(Adw.Dialog):
    __gtype_name__ = "DisquaireGenresDialog"

    def __init__(self, library_genres, on_replace):
        """`library_genres` : {genre: nombre de morceaux} ; `on_replace(old, new)`."""
        super().__init__(title="Genres", content_width=620, content_height=680)
        from . import genres
        self._genres = genres
        self._items = genres.load()
        self._library = library_genres
        self._on_replace = on_replace

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher(policy=Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)
        toolbar.add_top_bar(header)
        stack = Adw.ViewStack()
        switcher.set_stack(stack)

        # --- liste proposée ------------------------------------------------
        page = Adw.PreferencesPage()
        add_group = Adw.PreferencesGroup(
            description="Seuls ces genres sont proposés dans le champ Genre. "
                        "Un genre absent de la liste peut toujours être tapé à la main.")
        self.add_row = Adw.EntryRow(title="Ajouter un genre", show_apply_button=True)
        self.add_row.connect("apply", self._add)
        add_group.add(self.add_row)
        page.add(add_group)
        self.list_group = Adw.PreferencesGroup(title="Genres proposés")
        reset = Gtk.Button(label="Liste d'origine", valign=Gtk.Align.CENTER)
        reset.add_css_class("flat")
        reset.connect("clicked", lambda *_: self._set_items(list(genres.DEFAULT)))
        self.list_group.set_header_suffix(reset)
        page.add(self.list_group)
        self._list_rows = []
        stack.add_titled_with_icon(page, "list", "Liste", "view-list-symbolic")

        # --- genres de la discothèque --------------------------------------
        lib_page = Adw.PreferencesPage()
        self.lib_group = Adw.PreferencesGroup(
            description="Genres trouvés dans vos morceaux. Ceux qui ne sont pas dans "
                        "la liste peuvent être remplacés, partout, par un genre de la liste.")
        lib_page.add(self.lib_group)
        self._lib_rows = []
        stack.add_titled_with_icon(lib_page, "library", "Discothèque", "disquaire-music-symbolic")

        toolbar.set_content(stack)
        self.toasts = Adw.ToastOverlay(child=toolbar)
        self.set_child(self.toasts)
        self._fill_list()
        self._fill_library()

    # --- liste ----------------------------------------------------------
    def _set_items(self, items):
        self._genres.save(items)
        self._items = self._genres.load()
        self._fill_list()
        self._fill_library()

    def _fill_list(self):
        for r in self._list_rows:
            self.list_group.remove(r)
        self._list_rows = []
        for g in self._items:
            row = Adw.ActionRow(title=GLib.markup_escape_text(g))
            ed = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER,
                            tooltip_text="Renommer")
            ed.add_css_class("flat")
            ed.connect("clicked", lambda _b, old=g: ask_name(
                self, "Renommer le genre", old, lambda new, o=old: self._rename(o, new),
                "Renommer"))
            row.add_suffix(ed)
            rm = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                            tooltip_text="Retirer de la liste")
            rm.add_css_class("flat")
            rm.connect("clicked", lambda _b, old=g: self._set_items(
                [x for x in self._items if x != old]))
            row.add_suffix(rm)
            self.list_group.add(row)
            self._list_rows.append(row)

    def _add(self, row):
        text = textfmt_clean(row.get_text())
        if text:
            self._set_items(self._items + [text])
            row.set_text("")

    def _rename(self, old, new):
        new = textfmt_clean(new)
        if new and new != old:
            self._set_items([new if x == old else x for x in self._items])

    # --- discothèque ----------------------------------------------------
    def _fill_library(self):
        for r in self._lib_rows:
            self.lib_group.remove(r)
        self._lib_rows = []
        for g, n in sorted(self._library.items(), key=lambda kv: -kv[1]):
            canon = self._genres.canonical(g, self._items)
            in_list = canon == g
            row = Adw.ActionRow(title=GLib.markup_escape_text(g),
                                subtitle=f"{n} morceau{'x' if n > 1 else ''}"
                                + ("" if in_list else " · hors liste"))
            if in_list:
                ok = Gtk.Label(label="Dans la liste", valign=Gtk.Align.CENTER)
                ok.add_css_class("keep-badge")
                row.add_suffix(ok)
            else:
                model = Gtk.StringList.new(self._items)
                drop = Gtk.DropDown(model=model, valign=Gtk.Align.CENTER, enable_search=True)
                if canon:
                    drop.set_selected(self._items.index(canon))
                go = Gtk.Button(label="Remplacer", valign=Gtk.Align.CENTER)
                go.add_css_class("suggested-action")
                go.connect("clicked", lambda _b, old=g, d=drop: self._replace(
                    old, self._items[d.get_selected()]))
                row.add_suffix(drop)
                row.add_suffix(go)
            self.lib_group.add(row)
            self._lib_rows.append(row)

    def _replace(self, old, new):
        n = self._library.pop(old, 0)
        self._library[new] = self._library.get(new, 0) + n
        self._fill_library()
        self._on_replace(old, new)


def textfmt_clean(text: str) -> str:
    from .textfmt import clean_spaces
    return clean_spaces(text)


def textfmt_key(text):
    from .textfmt import match_key
    return match_key(text)
