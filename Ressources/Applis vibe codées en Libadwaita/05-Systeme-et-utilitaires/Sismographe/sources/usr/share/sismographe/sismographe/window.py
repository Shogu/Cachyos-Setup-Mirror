"""Fenêtre principale : chargement des données et navigation."""
import threading
from concurrent.futures import ThreadPoolExecutor

from gi.repository import Adw, Gio, GLib, Gtk, Pango

from . import report
from . import sources as s
from . import widgets as w
from .boot import BootPage
from .health import HealthPage
from .journal import JournalPage
from .storage import StoragePage

APP_ID = "io.github.ogu.Sismographe"

COLLECTORS = {
    "state": s.system_state,
    "failed": lambda: s.failed_units(False),
    "failed_user": lambda: s.failed_units(True),
    "errors": lambda: s.journal("0", "all", (0, 3)),
    "errors_prev": lambda: s.journal("-1", "all", (0, 3)),
    "shutdown": s.previous_shutdown,
    "params": lambda: s.kernel_parameters("0"),
    "taint": s.taint,
    "coredumps": s.coredumps,
    "space": s.space,
    "boots": s.boots,
    "analyze": lambda: s.analyze(False),
    "analyze_user": lambda: s.analyze(True),
    "blame": lambda: s.blame(False),
    "blame_user": lambda: s.blame(True),
    "chain": lambda: s.critical_chain(False),
    "chain_user": lambda: s.critical_chain(True),
}


class Window(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Sismographe")
        self.set_default_size(1060, 760)
        self.set_size_request(360, 420)
        self.data = {}
        self.loading = set()
        self.generation = 0
        self.pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="sismo")
        self.build()
        self.install_actions()
        self.reload()

    # ------------------------------------------------------------------ construction
    def build(self):
        self.toasts = Adw.ToastOverlay()
        self.nav = Adw.NavigationView()
        self.toasts.set_child(self.nav)
        self.set_content(self.toasts)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Tout relire (Ctrl+R)")
        refresh.set_action_name("win.reload")
        header.pack_start(refresh)
        menu = Gio.Menu()
        section = Gio.Menu()
        section.append("Copier le rapport complet", "win.copy-report")
        section.append("Exporter le rapport…", "win.export")
        menu.append_section(None, section)
        about = Gio.Menu()
        about.append("Raccourcis clavier", "win.shortcuts")
        about.append("À propos de Sismographe", "app.about")
        menu.append_section(None, about)
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                       tooltip_text="Menu principal", primary=True))

        self.stack = Adw.ViewStack()
        self.health = HealthPage(self)
        self.journal = JournalPage(self)
        self.boot = BootPage(self)
        self.storage = StoragePage(self)
        self.stack.add_titled_with_icon(self.health, "health", "Santé", f"{APP_ID}-symbolic")
        self.stack.add_titled_with_icon(self.journal, "journal", "Journaux", "text-x-generic-symbolic")
        self.stack.add_titled_with_icon(self.boot, "boot", "Démarrage", "system-reboot-symbolic")
        self.stack.add_titled_with_icon(self.storage, "storage", "Stockage", "drive-harddisk-symbolic")
        self.stack.connect("notify::visible-child-name", self.page_changed)
        toolbar.set_content(self.stack)

        switcher = Adw.ViewSwitcher(stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)
        bar = Adw.ViewSwitcherBar(stack=self.stack)
        toolbar.add_bottom_bar(bar)
        narrow = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 680sp"))
        narrow.add_setter(bar, "reveal", True)
        narrow.add_setter(header, "title-widget", Adw.WindowTitle(title="Sismographe"))
        narrow.add_setter(self.journal.controls, "orientation", Gtk.Orientation.VERTICAL)
        self.add_breakpoint(narrow)

        self.nav.add(Adw.NavigationPage(child=toolbar, title="Sismographe", tag="main"))

    def install_actions(self):
        for name, callback in (("reload", lambda *_: self.reload()),
                               ("copy-report", lambda *_: self.copy_report()),
                               ("export", lambda *_: self.export_report()),
                               ("find", lambda *_: self.focus_search()),
                               ("shortcuts", lambda *_: self.show_shortcuts())):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
        app = self.get_application()
        app.set_accels_for_action("win.reload", ["<Control>r", "F5"])
        app.set_accels_for_action("win.find", ["<Control>f"])
        app.set_accels_for_action("win.copy-report", ["<Control><Shift>c"])
        app.set_accels_for_action("win.export", ["<Control>s"])
        app.set_accels_for_action("win.shortcuts", ["<Control>question"])
        for i, name in enumerate(("health", "journal", "boot", "storage"), start=1):
            action = Gio.SimpleAction.new(f"page-{name}", None)
            action.connect("activate", lambda *_a, n=name: self.stack.set_visible_child_name(n))
            self.add_action(action)
            app.set_accels_for_action(f"win.page-{name}", [f"<Alt>{i}"])

    SHORTCUTS = (("<Control>r", "Tout relire"), ("<Control>f", "Filtrer les journaux"),
                 ("<Control><Shift>c", "Copier le rapport complet"), ("<Control>s", "Exporter le rapport"),
                 ("<Alt>1", "Santé"), ("<Alt>2", "Journaux"), ("<Alt>3", "Démarrage"),
                 ("<Alt>4", "Stockage"), ("<Control>question", "Raccourcis clavier"))

    def show_shortcuts(self):
        dialog = Adw.ShortcutsDialog()
        section = Adw.ShortcutsSection(title="Général")
        for accel, title in self.SHORTCUTS:
            section.add(Adw.ShortcutsItem(title=title, accelerator=accel))
        dialog.add(section)
        dialog.present(self)

    # ------------------------------------------------------------------ données
    def reload(self):
        self.generation += 1
        token = self.generation
        keep = {k: v for k, v in self.data.items() if k == "hardware"}
        self.data = keep
        self.loading = set(COLLECTORS)
        self.refresh_pages()
        for key, func in COLLECTORS.items():
            self.pool.submit(self.collect, token, key, func)
        if self.journal.loaded_key is not None:
            self.journal.reload(force=True)

    def collect(self, token, key, func):
        try:
            result = func()
        except Exception as exc:          # un collecteur ne doit jamais faire tomber l’appli
            result = s.Result("failed", detail=f"{type(exc).__name__} : {exc}")
        GLib.idle_add(self.collected, token, key, result)

    def collected(self, token, key, result):
        if token != self.generation:
            return GLib.SOURCE_REMOVE
        self.data[key] = result
        self.loading.discard(key)
        if key == "boots":
            self.journal.set_boots(result)
        # on regroupe les redessins : un seul par passage de la boucle
        if not getattr(self, "_refresh_pending", False):
            self._refresh_pending = True
            GLib.timeout_add(60, self.refresh_pages)
        return GLib.SOURCE_REMOVE

    def refresh_pages(self):
        self._refresh_pending = False
        self.health.refresh()
        self.boot.refresh()
        self.storage.refresh()
        return GLib.SOURCE_REMOVE

    def run_hardware(self):
        if "hardware" in self.loading:
            return
        self.loading.add("hardware")
        self.refresh_pages()

        def work():
            result = s.hardware()
            GLib.idle_add(self.hardware_done, result)

        threading.Thread(target=work, daemon=True).start()

    def hardware_done(self, result):
        self.loading.discard("hardware")
        if result.status == "denied" and self.data.get("hardware") is not None:
            self.toast(result.detail)
        else:
            self.data["hardware"] = result
        self.refresh_pages()
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ navigation
    def page_changed(self, *_):
        if self.stack.get_visible_child_name() == "journal":
            self.journal.ensure_loaded()

    def focus_search(self):
        self.nav.pop_to_tag("main")
        self.stack.set_visible_child_name("journal")
        self.journal.search.grab_focus()

    def show_unit(self, unit, scope="all"):
        self.nav.pop_to_tag("main")
        self.stack.set_visible_child_name("journal")
        self.journal.show_unit(unit, scope)

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=3))

    def open_errors(self, boot, title):
        res = self.data.get("errors" if boot == "0" else "errors_prev")
        if not res or not res.value:
            return
        page = Adw.PreferencesPage()
        groups = s.group(res.value)
        g = Adw.PreferencesGroup(title=f"{len(groups)} groupes de messages semblables",
                                 description="Du plus grave au moins grave, puis du plus fréquent au plus rare.")
        g.set_header_suffix(w.button("Tout copier", "edit-copy-symbolic", css=("flat",), callback=lambda: (
            w.copy_text(self, "\n".join(f"[{s.LEVELS[e.priority]}] {e.unit} ×{n} — {e.message.strip()}"
                                        for e, n in groups)), self.toast("Liste copiée"))))
        for event, count in groups[:200]:
            r = w.row(event.message.splitlines()[0][:150],
                      f"{event.unit} · {s.LEVELS[event.priority]} · {event.clock()} · ×{count}",
                      activatable=True)
            r.add_prefix(w.level_pill(event.priority, s.SHORT_LEVELS[event.priority]))
            r.connect("activated", lambda _r, e=event, n=count: self.open_event(e, n, boot))
            g.add(r)
        page.add(g)
        self.push(page, title, report.boot_label(boot).capitalize())

    def push(self, content, title, subtitle=""):
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=title, subtitle=subtitle))
        toolbar.add_top_bar(header)
        toolbar.set_content(content)
        self.nav.push(Adw.NavigationPage(child=toolbar, title=title))

    def open_event(self, event, count=1, boot="0", neighbours=None):
        page = Adw.PreferencesPage()
        head = Adw.PreferencesGroup()
        msg = Gtk.Label(label=event.message.strip(), xalign=0, wrap=True, selectable=True)
        msg.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        msg.set_can_focus(False)          # sélectionnable à la souris, sans tout surligner à l’ouverture
        msg.add_css_class("title-4")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        line = Gtk.Box(spacing=8)
        line.append(w.level_pill(event.priority, s.LEVELS[event.priority]))
        unit = Gtk.Label(label=event.unit, xalign=0)
        unit.add_css_class("unit-label")
        line.append(unit)
        box.append(line)
        box.append(msg)
        head.add(box)
        page.add(head)

        context_group = Adw.PreferencesGroup(title="Contexte",
                                             description="Même unité, une minute avant et après")
        context_holder = {"events": neighbours or [event]}

        # bouton principal seul, actions secondaires discrètes dessous : tient dans 360 px
        actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6,
                          halign=Gtk.Align.START)
        paste = w.button("Copier pour coller", "edit-paste-symbolic", css=("suggested-action", "pill"),
                         tooltip="Bloc prêt à coller dans un forum, un ticket ou une discussion",
                         callback=lambda: (w.copy_text(self, report.event_block(
                             event, count, boot, context_holder["events"])),
                             self.toast("Erreur copiée, prête à coller")))
        paste.set_halign(Gtk.Align.START)
        actions.append(paste)
        secondary = Gtk.Box(spacing=4)
        secondary.append(w.button("Message seul", "edit-copy-symbolic", css=("flat",), callback=lambda: (
            w.copy_text(self, event.message.strip()), self.toast("Message copié"))))
        if event.source != "pacman":
            secondary.append(w.button("Journal de l’unité", "text-x-generic-symbolic", css=("flat",),
                                      callback=lambda: self.show_unit(event.unit,
                                                                      "user" if event.source == "user" else "all")))
        actions.append(secondary)
        head.add(actions)

        info = Adw.PreferencesGroup(title="Détails")
        info.add(w.row("Date", value=event.full_date))
        info.add(w.row("Niveau", value=f"{s.LEVELS[event.priority]} ({event.priority})"))
        if event.pid:
            info.add(w.row("PID", value=event.pid))
        if count > 1:
            info.add(w.row("Messages semblables", value=str(count)))
        info.add(w.row("Origine", value=("journal pacman" if event.source == "pacman"
                                         else report.boot_label(boot))))
        page.add(info)
        page.add(context_group)
        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        context_group.add(holder)

        def show(events):
            child = holder.get_first_child()
            while child:
                holder.remove(child)
                child = holder.get_first_child()
            context_holder["events"] = events
            text = "\n".join(f"{'→' if e == event else ' '} {e.clock(e.source == 'pacman')}  "
                             f"{s.SHORT_LEVELS[e.priority]}  {e.message.strip().replace(chr(10), ' ⏎ ')}"
                             for e in events)
            holder.append(w.mono_block(text or "(rien d’autre)", wrap=True))

        if neighbours is not None or event.source == "pacman":
            show(neighbours or [event])
        else:
            holder.append(w.spinner(24))
            sec = event.timestamp // 1_000_000

            def work():
                scope = "kernel" if event.unit == "kernel" else ("user" if event.source == "user" else "all")
                res = s.journal(boot, scope, None, limit=2000, unit=event.unit, since=sec - 60, until=sec + 61)
                events = sorted(res.value or [], key=lambda e: e.timestamp)[-60:] if res.status == "ok" else []
                if event not in events:
                    events = sorted(events + [event], key=lambda e: e.timestamp)
                GLib.idle_add(lambda: (show(events), GLib.SOURCE_REMOVE)[1])

            threading.Thread(target=work, daemon=True).start()
        self.push(page, "Événement", f"{event.unit} · {event.clock(event.source == 'pacman')}")
        GLib.idle_add(lambda: (paste.grab_focus(), GLib.SOURCE_REMOVE)[1])

    # ------------------------------------------------------------------ rapport
    def copy_report(self):
        w.copy_text(self, report.full_report(self.data))
        self.toast("Rapport complet copié")

    def export_report(self):
        dialog = Gtk.FileDialog(title="Exporter le rapport", initial_name="sismographe-rapport.txt")
        dialog.save(self, None, self.export_done)

    def export_done(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        try:
            gfile.replace_contents(report.full_report(self.data).encode("utf-8"), None, False,
                                   Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            self.toast(f"Rapport enregistré : {gfile.get_basename()}")
        except GLib.Error as exc:
            self.toast(f"Export impossible : {exc.message}")
