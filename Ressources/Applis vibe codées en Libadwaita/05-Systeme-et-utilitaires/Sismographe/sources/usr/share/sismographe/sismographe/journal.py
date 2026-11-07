"""Page Journaux : journald (système, session, noyau) et pacman dans une seule liste."""
import datetime
import threading

from gi.repository import Adw, Gio, GLib, GObject, Gtk, Pango

from . import sources as s
from . import widgets as w

SOURCES = (("all", "Tout journald"), ("system", "Système"), ("user", "Session utilisateur"),
           ("kernel", "Noyau (dmesg)"), ("pacman", "Pacman"))
PRIORITIES = (("Erreurs (0–3)", (0, 3)), ("Avertissements et plus (0–4)", (0, 4)),
              ("Avertissements seuls (4)", (4, 4)), ("Notices et plus (0–5)", (0, 5)),
              ("Tout (0–7)", None))


class EventObject(GObject.Object):
    __gtype_name__ = "SismographeEvent"

    def __init__(self, event):
        super().__init__()
        self.event = event
        self.haystack = f"{event.unit} {event.message}".casefold()


class JournalPage(Gtk.Box):
    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.window = window
        self.generation = 0
        self.boot_ids = ["0"]
        self.partial = False
        self.loaded_key = None
        self.busy = False
        self.failed = False

        controls = Gtk.Box(spacing=8)
        controls.add_css_class("journal-controls")
        self.controls = controls
        self.source = Gtk.DropDown.new_from_strings([t for _, t in SOURCES])
        self.source.set_tooltip_text("Source")
        self.boot = Gtk.DropDown.new_from_strings(["Démarrage actuel"])
        self.boot.set_tooltip_text("Démarrage")
        self.priority = Gtk.DropDown.new_from_strings([t for t, _ in PRIORITIES])
        self.priority.set_tooltip_text("Gravité")
        self.search = Gtk.SearchEntry(placeholder_text="Filtrer (unité ou texte)", hexpand=True)
        self.source.connect("notify::selected", self.source_changed)
        for widget in (self.boot, self.priority):
            widget.connect("notify::selected", lambda *_: self.reload())
        # côte à côte ; la fenêtre étroite les empile (point de rupture dans window.py)
        for widget in (self.source, self.boot, self.priority):
            widget.set_valign(Gtk.Align.CENTER)
            controls.append(widget)
        self.search.set_valign(Gtk.Align.CENTER)
        self.search.set_size_request(180, -1)
        controls.append(self.search)
        self.search.connect("search-changed", lambda *_: self.refilter())
        self.append(controls)
        self.append(Gtk.Separator())

        self.store = Gio.ListStore(item_type=EventObject)
        self.filter = Gtk.CustomFilter.new(self.match)
        filtered = Gtk.FilterListModel(model=self.store, filter=self.filter)
        filtered.connect("items-changed", lambda *_: self.update_footer())
        self.filtered = filtered
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.setup_row)
        factory.connect("bind", self.bind_row)
        self.list = Gtk.ListView(model=Gtk.NoSelection(model=filtered), factory=factory,
                                 single_click_activate=True)
        self.list.add_css_class("navigation-sidebar")
        self.list.connect("activate", self.activated)
        scroll = Gtk.ScrolledWindow(vexpand=True, child=self.list)

        self.views = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, vexpand=True)
        self.views.add_named(scroll, "list")
        self.views.add_named(w.loading_page("Lecture du journal…"), "loading")
        self.empty = Adw.StatusPage(icon_name="io.github.ogu.Sismographe-symbolic",
                                    title="Calme plat", description="Aucun événement pour ces filtres.")
        self.views.add_named(self.empty, "empty")
        self.error = Adw.StatusPage(icon_name="dialog-warning-symbolic", title="Journal illisible")
        self.views.add_named(self.error, "error")
        self.append(self.views)

        self.footer = Gtk.Label(xalign=0, margin_start=12, margin_end=12, margin_top=4, margin_bottom=6,
                                ellipsize=Pango.EllipsizeMode.END)
        self.footer.add_css_class("caption")
        self.footer.add_css_class("dim-label")
        self.append(self.footer)

    # ------------------------------------------------------------------ démarrages
    def set_boots(self, result):
        if not result or not result.ok:
            return
        labels, ids = [], []
        for b in result.value:
            first = datetime.datetime.fromtimestamp(b["first"] / 1e6) if b["first"] else None
            last = datetime.datetime.fromtimestamp(b["last"] / 1e6) if b["last"] else None
            if b["index"] == 0:
                name = "Démarrage actuel"
            elif b["index"] == -1:
                name = "Démarrage précédent"
            else:
                name = f"Démarrage {b['index']}"
            span = ""
            if first:
                span = first.strftime(" · %d/%m %H:%M")
                if last and b["index"] != 0:
                    span += last.strftime(" → %H:%M") if last.date() == first.date() else last.strftime(" → %d/%m %H:%M")
            labels.append(name + span)
            ids.append(str(b["index"]))
        current = self.boot_ids[self.boot.get_selected()] if self.boot_ids else "0"
        self.boot_ids = ids
        self.boot.set_model(Gtk.StringList.new(labels))
        self.boot.set_selected(ids.index(current) if current in ids else 0)

    # ------------------------------------------------------------------ chargement
    def params(self):
        source = SOURCES[self.source.get_selected()][0]
        boot = self.boot_ids[self.boot.get_selected()] if self.boot.get_selected() < len(self.boot_ids) else "0"
        priority = PRIORITIES[self.priority.get_selected()][1]
        return source, boot, priority

    def source_changed(self, *_):
        # pour pacman, l’intérêt est l’historique des mises à jour : on montre les notices
        if SOURCES[self.source.get_selected()][0] == "pacman" and self.priority.get_selected() == 0:
            self.priority.set_selected(3)          # déclenche reload()
        else:
            self.reload()

    def ensure_loaded(self):
        if self.loaded_key is None:
            self.reload()

    def reload(self, force=False):
        source, boot, priority = self.params()
        self.boot.set_sensitive(source != "pacman")
        key = (source, boot, priority)
        if key == self.loaded_key and not force:
            return
        self.loaded_key = key
        self.generation += 1
        token = self.generation
        self.busy, self.failed = True, False
        self.views.set_visible_child_name("loading")
        self.footer.set_text("")

        def work():
            if source == "pacman":
                res = s.pacman_log()
                if res.ok and priority:
                    lo, hi = priority
                    res = s.Result("ok", [e for e in res.value if lo <= e.priority <= hi])
            else:
                res = s.journal(boot, source, priority)
            GLib.idle_add(self.loaded, token, res)

        threading.Thread(target=work, daemon=True).start()

    def loaded(self, token, res):
        if token != self.generation:
            return GLib.SOURCE_REMOVE
        self.partial = res.detail == "partial"
        self.busy = False
        if res.status not in ("ok", "empty"):
            self.failed = True
            self.error.set_description(res.detail or res.status)
            self.views.set_visible_child_name("error")
            self.store.remove_all()
            return GLib.SOURCE_REMOVE
        events = sorted(res.value or [], key=lambda e: e.timestamp, reverse=True)
        self.store.splice(0, self.store.get_n_items(), [EventObject(e) for e in events])
        self.update_footer()
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ filtre
    def match(self, item):
        query = self.search.get_text().strip().casefold()
        return not query or query in item.haystack

    def refilter(self):
        self.filter.changed(Gtk.FilterChange.DIFFERENT)
        self.update_footer()

    def update_footer(self):
        total = self.store.get_n_items()
        shown = self.filtered.get_n_items()
        if self.busy or self.failed:
            return
        self.views.set_visible_child_name("list" if shown else "empty")
        text = f"{shown} événement{'s' if shown > 1 else ''}"
        if shown != total:
            text += f" sur {total}"
        if total >= 20000:
            text += " · limité aux 20 000 plus récents"
        if self.partial:
            text += " · journal partiel : ajoutez-vous au groupe wheel ou systemd-journal"
        self.footer.set_text(text)

    def show_unit(self, unit, scope="all"):
        self.source.set_selected([k for k, _ in SOURCES].index(scope if scope in ("all", "user") else "all"))
        self.priority.set_selected(len(PRIORITIES) - 1)
        self.search.set_text(unit)
        self.reload()

    # ------------------------------------------------------------------ lignes
    def setup_row(self, _factory, item):
        box = Gtk.Box(spacing=12)
        box.add_css_class("event-row")
        clock = Gtk.Label(xalign=0, width_chars=8)
        clock.add_css_class("monospace")
        clock.add_css_class("dim-label")
        clock.add_css_class("caption")
        level = Gtk.Label(width_chars=4)
        level.add_css_class("lvl")
        unit = Gtk.Label(xalign=0, width_chars=20, max_width_chars=20, ellipsize=Pango.EllipsizeMode.END)
        unit.add_css_class("unit-label")
        message = Gtk.Label(xalign=0, hexpand=True, ellipsize=Pango.EllipsizeMode.END, single_line_mode=True)
        for widget in (clock, level, unit, message):
            box.append(widget)
        item.set_child(box)

    def bind_row(self, _factory, item):
        event = item.get_item().event
        clock, level, unit, message = self.children(item.get_child())
        clock.set_text(event.clock(event.source == "pacman"))
        for cls in ("lvl-err", "lvl-warn", "lvl-notice", "lvl-info"):
            level.remove_css_class(cls)
        level.add_css_class(w.LEVEL_CLASS[event.priority])
        level.set_text(s.SHORT_LEVELS[event.priority])
        level.set_tooltip_text(s.LEVELS[event.priority])
        unit.set_text(event.unit)
        unit.set_tooltip_text(event.unit)
        message.set_text(event.message.replace("\n", " ⏎ ")[:400])

    @staticmethod
    def children(box):
        out, child = [], box.get_first_child()
        while child:
            out.append(child)
            child = child.get_next_sibling()
        return out

    def activated(self, _list, position):
        event = self.filtered.get_item(position).event
        source, boot, _ = self.params()
        neighbours = None
        if source == "pacman":
            items = [self.store.get_item(i).event for i in range(self.store.get_n_items())]
            idx = items.index(event)
            neighbours = list(reversed(items[max(0, idx - 8): idx + 9]))
        self.window.open_event(event, 1, boot, neighbours)
