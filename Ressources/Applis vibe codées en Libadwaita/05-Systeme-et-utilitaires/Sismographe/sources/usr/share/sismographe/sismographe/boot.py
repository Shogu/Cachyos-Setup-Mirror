"""Page Démarrage : systemd-analyze time, blame et critical-chain, système ou session."""
from gi.repository import Adw, Gtk

from . import sources as s
from . import widgets as w

STAGES = {"firmware": ("Micrologiciel (UEFI)", (0.38, 0.21, 0.71)),
          "loader": ("Chargeur d’amorçage", (0.11, 0.44, 0.85)),
          "kernel": ("Noyau", (0.15, 0.64, 0.41)),
          "initrd": ("Initramfs", (0.90, 0.65, 0.04)),
          "userspace": ("Espace utilisateur", (0.88, 0.38, 0.0))}


class BootPage(Adw.Bin):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.user = False
        self.show_all = False
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        switch = Gtk.Box(halign=Gtk.Align.CENTER, margin_top=12)
        switch.add_css_class("linked")
        self.system_btn = Gtk.ToggleButton(label="Système", active=True)
        self.user_btn = Gtk.ToggleButton(label="Session utilisateur", group=self.system_btn)
        self.system_btn.connect("toggled", self.toggled)
        switch.append(self.system_btn)
        switch.append(self.user_btn)
        box.append(switch)
        self.page = Adw.PreferencesPage(vexpand=True)
        box.append(self.page)
        self.set_child(box)
        self.groups = []

    def toggled(self, button):
        self.user = not self.system_btn.get_active()
        self.refresh()

    def key(self, name):
        return name + ("_user" if self.user else "")

    def refresh(self):
        w.clear_page(self.page, self.groups)
        self.timing()
        self.blame()
        self.chain()

    def add(self, title, description=None):
        g = Adw.PreferencesGroup(title=title)
        if description:
            g.set_description(description)
        self.page.add(g)
        self.groups.append(g)
        return g

    # ------------------------------------------------------------------ durées
    def timing(self):
        g = self.add("Durée du démarrage" if not self.user else "Durée d’ouverture de session")
        res = self.window.data.get(self.key("analyze"))
        if res is None:
            g.add(w.row("Mesure", "systemd-analyze…", "wait"))
            return
        if not res.ok:
            g.add(w.row("Mesure indisponible", res.detail or res.status, "off"))
            return
        stages = [(k, v) for k, v in res.value["stages"] if v > 0]
        if res.value["target"]:
            g.set_description(res.value["target"])
        if len(stages) > 1:
            area = Gtk.DrawingArea(content_height=22, hexpand=True)
            area.set_draw_func(self.draw_bar, stages)
            g.add(area)
            g = self.add("")
        for key, sec in stages:
            name, color = STAGES.get(key, (key, (0.5, 0.5, 0.5)))
            r = w.row(name, value=s.human(sec))
            dot = Gtk.DrawingArea(content_width=12, content_height=12, valign=Gtk.Align.CENTER)
            dot.set_draw_func(lambda _a, cr, wd, ht, c=color: (cr.set_source_rgb(*c),
                                                               cr.arc(wd / 2, ht / 2, 6, 0, 6.2832), cr.fill()))
            r.add_prefix(dot)
            g.add(r)
        total = w.row("Total", value=s.human(res.value["total"]))
        g.add(total)

    @staticmethod
    def draw_bar(_area, cr, width, height, stages):
        total = sum(v for _, v in stages) or 1
        x = 0.0
        radius = height / 2
        cr.new_sub_path()
        cr.arc(radius, radius, radius, 1.5708, 4.7124)
        cr.arc(width - radius, radius, radius, 4.7124, 1.5708)
        cr.close_path()
        cr.clip()
        for key, sec in stages:
            seg = width * sec / total
            cr.set_source_rgb(*STAGES.get(key, ("", (0.5, 0.5, 0.5)))[1])
            cr.rectangle(x, 0, seg + 0.5, height)
            cr.fill()
            x += seg

    # ------------------------------------------------------------------ blame
    def blame(self):
        g = self.add("Unités les plus lentes", "systemd-analyze blame : temps d’initialisation de chaque unité")
        res = self.window.data.get(self.key("blame"))
        if res is None:
            g.add(w.row("Lecture…", status="wait"))
            return
        if not res.ok:
            g.add(w.row("Indisponible", res.detail or res.status, "off"))
            return
        rows = res.value
        g.set_header_suffix(w.button("Copier", "edit-copy-symbolic", css=("flat",), callback=lambda: (
            w.copy_text(self, "\n".join(f"{s.human(sec):>12}  {u}" for u, sec in rows)),
            self.window.toast("Liste copiée"))))
        top = rows[0][1] or 1
        limit = len(rows) if self.show_all else 25
        for unit, sec in rows[:limit]:
            kind = "error" if sec >= 10 else "warn" if sec >= 3 else None
            r = w.row(unit, status=kind)
            bar = Gtk.LevelBar(min_value=0, max_value=top, value=sec, valign=Gtk.Align.CENTER)
            bar.set_size_request(120, -1)
            bar.remove_offset_value("low")
            bar.remove_offset_value("high")
            bar.remove_offset_value("full")
            r.add_suffix(bar)
            lab = w.value_label(s.human(sec))
            lab.set_width_chars(10)
            r.add_suffix(lab)
            if not self.user:
                r.set_activatable(True)
                r.connect("activated", lambda _r, u=unit: self.window.show_unit(u.removesuffix(".service"), "all"))
            g.add(r)
        if len(rows) > 25:
            more = w.button("Tout afficher" if not self.show_all else "Réduire", css=("flat",),
                            callback=self.toggle_all)
            more.set_margin_top(6)
            g.add(more)

    def toggle_all(self):
        self.show_all = not self.show_all
        self.refresh()

    # ------------------------------------------------------------------ chaîne critique
    def chain(self):
        g = self.add("Chaîne critique",
                     "« @ » : moment où l’unité est devenue active · « + » : durée de son démarrage")
        res = self.window.data.get(self.key("chain"))
        if res is None:
            g.add(w.row("Lecture…", status="wait"))
            return
        if not res.ok:
            g.add(w.row("Indisponible", res.detail or res.status, "off"))
            return
        g.set_header_suffix(w.button("Copier", "edit-copy-symbolic", css=("flat",), callback=lambda: (
            w.copy_text(self, res.value), self.window.toast("Chaîne critique copiée"))))
        g.add(w.mono_block(res.value))
