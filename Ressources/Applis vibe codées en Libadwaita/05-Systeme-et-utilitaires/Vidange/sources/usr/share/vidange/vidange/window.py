"""Vidange — fenêtre principale, pages de paquets, récapitulatif."""

import threading

from gi.repository import Adw, Gio, GLib, Gtk

from . import backend as be

ICONS = {
    "orphans": "package-x-generic-symbolic",
    "unneeded": "view-list-bullet-symbolic",
    "explicit": "user-available-symbolic",
    "pacman": "folder-download-symbolic",
    "aur": "applications-engineering-symbolic",
    "journal": "text-x-generic-symbolic",
    "home": "user-trash-symbolic",
    "dev": "utilities-terminal-symbolic",
    "browsers": "web-browser-symbolic",
    "fwupd": "software-update-available-symbolic",
    "webcache": "network-server-symbolic",
    "shaders": "video-display-symbolic",
    "configs": "folder-symbolic",
    "flatpak": "system-software-install-symbolic",
    "containers": "drive-multidisk-symbolic",
}


def in_background(func, done, *args):
    """Exécute func(*args) dans un fil, puis done(résultat, erreur) dans GTK."""
    def worker():
        try:
            result, error = func(*args), None
        except Exception as exc:  # noqa: BLE001 — remonté à l'interface
            result, error = None, exc
        GLib.idle_add(lambda: done(result, error) and False)
    threading.Thread(target=worker, daemon=True).start()


class Status(Gtk.Stack):
    """Suffixe d'une ligne : taille, roue d'attente, coche ou avertissement."""

    def __init__(self):
        super().__init__(valign=Gtk.Align.CENTER, hhomogeneous=False,
                         transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.label = Gtk.Label(label="…", css_classes=["dim-label", "numeric"])
        self.add_named(self.label, "size")
        self.add_named(Adw.Spinner(), "busy")
        self.add_named(Gtk.Image(icon_name="object-select-symbolic",
                                 css_classes=["success"]), "done")
        self.warn = Gtk.Image(icon_name="dialog-warning-symbolic",
                              css_classes=["warning"])
        self.add_named(self.warn, "error")

    def size(self, text):
        self.label.set_label(text)
        self.set_visible_child_name("size")

    def busy(self):
        self.set_visible_child_name("busy")

    def done(self, ok, message=""):
        self.warn.set_tooltip_text(message or None)
        self.set_visible_child_name("done" if ok else "error")


# ==========================================================================
# Pages de paquets (trois niveaux d'orphelins)
# ==========================================================================

class PackagePage(Adw.NavigationPage):
    TEXTS = {
        "orphans": (None, "Supprimer la sélection"),
        "unneeded": ("À vérifier avant suppression : ces paquets ne servent "
                     "qu'entre eux, ou seulement comme dépendances optionnelles.",
                     "Supprimer la sélection"),
        "explicit": ("Cette liste contient aussi les applis installées "
                     "volontairement. Vérifiez chaque paquet.",
                     "Marquer comme dépendance"),
        "configs": ("Correspondance devinée d'après les noms : vérifiez chaque "
                    "dossier. Ils partent à la corbeille, vous pouvez les récupérer.",
                    "Mettre à la corbeille"),
    }

    def __init__(self, win, kind):
        super().__init__(title=be.LABELS[kind], tag=kind)
        self.win, self.kind = win, kind
        banner_text, action = self.TEXTS[kind]

        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        rescan = Gtk.Button(icon_name="view-refresh-symbolic",
                            tooltip_text="Relancer la recherche")
        rescan.connect("clicked", lambda *_: win.do_search(kind))
        header.pack_end(rescan)
        view.add_top_bar(header)
        if banner_text:
            view.add_top_bar(Adw.Banner(title=banner_text, revealed=True))

        self.bin = Adw.Bin()
        view.set_content(self.bin)

        bar = Gtk.ActionBar()
        self.sel_label = Gtk.Label(css_classes=["dim-label"])
        bar.pack_start(self.sel_label)
        style = "suggested-action" if kind == "explicit" else "destructive-action"
        self.action_btn = Gtk.Button(label=action, css_classes=[style])
        self.action_btn.connect("clicked", self.on_action)
        bar.pack_end(self.action_btn)
        view.add_bottom_bar(bar)

        self.set_child(view)
        self.rebuild()

    @property
    def data(self):
        return self.win.lists[self.kind] or {"pkgs": [], "checked": set()}

    def rebuild(self):
        pkgs, checked = self.data["pkgs"], self.data["checked"]
        if not pkgs:
            self.bin.set_child(Adw.StatusPage(
                icon_name="object-select-symbolic",
                title="Aucun paquet trouvé",
                description="Rien à nettoyer à ce niveau."))
            self.update_selection()
            return

        page = Adw.PreferencesPage()
        word = "dossier" if self.kind == "configs" else "paquet"
        group = Adw.PreferencesGroup(
            title=f"{len(pkgs)} {word}{'s' if len(pkgs) > 1 else ''}")
        toggle_all = Gtk.Button(css_classes=["flat"], valign=Gtk.Align.CENTER,
                                label="Tout décocher" if checked else "Tout cocher")
        toggle_all.connect("clicked", self.on_toggle_all)
        group.set_header_suffix(toggle_all)

        if self.kind == "configs":
            for p in pkgs:
                row = Adw.ActionRow(title=p["display"], use_markup=False,
                                    subtitle=f"{be.fmt_size(p['size'])} · modifié le {p['date']}")
                check = Gtk.CheckButton(active=p["name"] in checked,
                                        valign=Gtk.Align.CENTER)
                check.connect("toggled", self.on_toggled, p["name"])
                row.add_prefix(check)
                row.set_activatable_widget(check)
                open_btn = Gtk.Button(icon_name="folder-open-symbolic",
                                      valign=Gtk.Align.CENTER, css_classes=["flat"],
                                      tooltip_text="Ouvrir dans Fichiers")
                open_btn.connect("clicked", self.on_open_folder, p["name"])
                row.add_suffix(open_btn)
                group.add(row)
            page.add(group)
            self.bin.set_child(page)
            self.update_selection()
            return

        for p in pkgs:
            row = Adw.ExpanderRow(title=p["name"], use_markup=False,
                                  subtitle=f"{p['version']} · {be.fmt_size(p['size'])}")
            check = Gtk.CheckButton(active=p["name"] in checked,
                                    valign=Gtk.Align.CENTER)
            check.connect("toggled", self.on_toggled, p["name"])
            row.add_prefix(check)
            for title, value in (("Description", p["desc"]),
                                 ("Requis par", p["required"]),
                                 ("Optionnel pour", p["optional"]),
                                 ("Installé le", p["date"])):
                sub = Adw.ActionRow(title=title, subtitle=value or "Aucun",
                                    use_markup=False, subtitle_selectable=True)
                sub.add_css_class("property")
                row.add_row(sub)
            group.add(row)
        page.add(group)
        self.bin.set_child(page)
        self.update_selection()

    def on_open_folder(self, _button, path):
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(path))
        launcher.launch(self.win, None, None)

    def update_selection(self):
        pkgs, checked = self.data["pkgs"], self.data["checked"]
        size = sum(p["size"] for p in pkgs if p["name"] in checked)
        n = len(checked)
        self.sel_label.set_label(
            f"{n} sélectionné{'s' if n > 1 else ''} · {be.fmt_size(size)}")
        self.action_btn.set_sensitive(n > 0 and not self.win.busy)

    def on_toggled(self, check, name):
        checked = self.data["checked"]
        if check.get_active():
            checked.add(name)
        else:
            checked.discard(name)
        self.update_selection()
        self.win.update_list_row(self.kind)

    def on_toggle_all(self, *_):
        data = self.data
        if data["checked"]:
            data["checked"].clear()
        else:
            data["checked"].update(p["name"] for p in data["pkgs"])
        self.rebuild()
        self.win.update_list_row(self.kind)

    def on_action(self, *_):
        names = sorted(self.data["checked"])
        if not names:
            return
        n = len(names)
        shown = ", ".join(names[:25]) + (" …" if n > 25 else "")
        if self.kind == "configs":
            shown = "\n".join(be._home_display(x) for x in names[:25]) + ("\n…" if n > 25 else "")
            heading = f"Mettre {n} dossier{'s' if n > 1 else ''} à la corbeille ?"
            body = f"{shown}\n\nVous pourrez les récupérer depuis la corbeille."
            label, appearance = "Mettre à la corbeille", Adw.ResponseAppearance.DESTRUCTIVE
        elif self.kind == "explicit":
            heading = f"Marquer {n} paquet{'s' if n > 1 else ''} comme dépendance ?"
            body = (f"{shown}\n\nCeux que rien n'utilise apparaîtront ensuite "
                    "parmi les orphelins simples.")
            label, appearance = "Marquer", Adw.ResponseAppearance.SUGGESTED
        else:
            heading = f"Supprimer {n} paquet{'s' if n > 1 else ''} ?"
            body = f"{shown}\n\nCommande : pacman -Rns"
            label, appearance = "Supprimer", Adw.ResponseAppearance.DESTRUCTIVE
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("ok", label)
        dialog.set_response_appearance("ok", appearance)
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _d, r: r == "ok"
                       and self.win.run_pkg_action(self.kind, names))
        dialog.present(self.win)


# ==========================================================================
# Fenêtre principale
# ==========================================================================

class VidangeWindow(Adw.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app, title="Vidange",
                         default_width=600, default_height=780)
        self.settings = be.load_settings()
        self.estimates = {}
        self.lists = {"orphans": None, "unneeded": None, "explicit": None,
                      "configs": None}
        self.status = {}
        self.rows = {}
        self.busy = False
        self.simulating = False

        simulate = Gio.SimpleAction.new_stateful(
            "simulate", None, GLib.Variant.new_boolean(False))
        simulate.connect("change-state", self.on_simulate)
        self.add_action(simulate)

        self.toasts = Adw.ToastOverlay()
        self.nav = Adw.NavigationView()
        self.toasts.set_child(self.nav)
        self.set_content(self.toasts)
        self.nav.add(self.build_main_page())
        self.refresh()

    # ---------------------------------------------------------------- build

    def build_main_page(self):
        page = Adw.NavigationPage(title="Vidange", tag="main")
        view = Adw.ToolbarView()

        header = Adw.HeaderBar()
        self.refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic",
                                      tooltip_text="Recalculer")
        self.refresh_btn.connect("clicked", lambda *_: self.refresh())
        header.pack_start(self.refresh_btn)
        menu = Gio.Menu()
        section = Gio.Menu()
        section.append("Mode simulation", "win.simulate")
        menu.append_section(None, section)
        about = Gio.Menu()
        about.append("À propos de Vidange", "app.about")
        menu.append_section(None, about)
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic",
                                       menu_model=menu, primary=True,
                                       tooltip_text="Menu principal"))
        view.add_top_bar(header)
        self.sim_banner = Adw.Banner(
            title="Mode simulation : rien ne sera supprimé ni modifié",
            button_label="Quitter",
            revealed=False)
        self.sim_banner.connect(
            "button-clicked",
            lambda *_: self.activate_action("win.simulate", None))
        view.add_top_bar(self.sim_banner)

        prefs = Adw.PreferencesPage()

        # --- Vérification : les quatre vues d'orphelins
        group = Adw.PreferencesGroup(
            title="Vérification",
            description="Seuls les orphelins sûrs font partie de « Tout nettoyer ». "
                        "Le reste s'examine au cas par cas.")
        group.add(self.make_row("orphans", Adw.ActionRow(
            title="Orphelins sûrs", subtitle="pacman -Qtdq · recherche non lancée"),
            search=True, switch=True, nav=True))
        group.add(self.make_row("unneeded", Adw.ActionRow(
            title="Orphelins à vérifier",
            subtitle="Dépendances qui ne servent qu'entre elles ou en option"),
            search=True, nav=True))
        group.add(self.make_row("explicit", Adw.ActionRow(
            title="Installés explicitement, à vérifier",
            subtitle="pacman -Qetq · rien ne les utilise"),
            search=True, nav=True))
        group.add(self.make_row("configs", Adw.ActionRow(
            title="Dossiers de configuration orphelins, à vérifier",
            subtitle="~/.config, ~/.local/share, ~/.cache, ~/.var/app"),
            search=True, nav=True))
        prefs.add(group)

        # --- Caches système
        group = Adw.PreferencesGroup(title="Caches système")
        # Ligne dépliable : chaque mode a sa ligne lisible, avec sa commande
        pacman = Adw.ExpanderRow(title="Cache pacman", subtitle_lines=2,
                                 subtitle=dict(be.PACMAN_MODES)[self.settings["pacman_mode"]])
        first = None
        for key, label in be.PACMAN_MODES:
            mode_row = Adw.ActionRow(title=label, subtitle=be.PACMAN_HINTS[key],
                                     use_markup=False, title_lines=0, subtitle_lines=0)
            radio = Gtk.CheckButton(valign=Gtk.Align.CENTER,
                                    active=key == self.settings["pacman_mode"])
            if first is None:
                first = radio
            else:
                radio.set_group(first)
            radio.connect("toggled", self.on_pacman_mode, key, pacman)
            mode_row.add_prefix(radio)
            mode_row.set_activatable_widget(radio)
            pacman.add_row(mode_row)
        group.add(self.make_row("pacman", pacman, switch=True))

        group.add(self.make_row("aur", Adw.ActionRow(
            title="Cache AUR",
            subtitle=("shelly purify standard --aur-cache"
                      if be.shelly_cache().is_dir() else "Aucun cache Shelly")),
            switch=True))

        group.add(self.make_row("flatpak", Adw.ActionRow(
            title="Flatpak inutilisés",
            subtitle=("flatpak uninstall --unused" if be.have("flatpak")
                      else "Flatpak n'est pas installé")), switch=True))

        journal = Adw.SpinRow.new_with_range(50, 4000, 50)
        journal.set_title("Journaux systemd")
        journal.set_subtitle("Taille conservée, en Mo")
        journal.set_value(self.settings["journal_mb"])
        journal.connect("notify::value", self.on_journal_size)
        group.add(self.make_row("journal", journal, switch=True))
        group.add(self.make_row("fwupd", Adw.ActionRow(
            title="Cache des micrologiciels", subtitle="/var/cache/fwupd"), switch=True))
        prefs.add(group)

        # --- Dossier personnel
        group = Adw.PreferencesGroup(title="Dossier personnel")
        group.add(self.make_row("home", Adw.ActionRow(
            title="Miniatures et corbeille"), switch=True))
        webs = [n for n, _, _ in be.web_caches()]
        group.add(self.make_row("webcache", Adw.ActionRow(
            title="Cache web des navigateurs",
            subtitle=(", ".join(webs) + " — navigateur fermé") if webs else "Aucun cache trouvé"),
            switch=True))
        shaders = sorted({n for n, _ in be.shader_dirs()})
        group.add(self.make_row("shaders", Adw.ActionRow(
            title="Caches de shaders",
            subtitle=", ".join(shaders) if shaders else "Aucun cache trouvé"), switch=True))
        dev = list(be.dev_dirs())
        group.add(self.make_row("dev", Adw.ActionRow(
            title="Caches de développement",
            subtitle=", ".join(dev) if dev else "Aucun cache trouvé"), switch=True))
        tools = be.container_tools()
        group.add(self.make_row("containers", Adw.ActionRow(
            title="Conteneurs",
            subtitle=(", ".join(tools) + " — cache de build et images orphelines")
            if tools else "Ni Docker ni Podman"), switch=True))
        found = [name for _, name, _ in be.browsers()]
        group.add(self.make_row("browsers", Adw.ActionRow(
            title="Navigateurs",
            subtitle="profile-cleaner : " + (", ".join(found) if found else "aucun profil")),
            switch=True))
        prefs.add(group)


        view.set_content(prefs)

        bar = Gtk.ActionBar()
        self.total_label = Gtk.Label(css_classes=["dim-label"])
        bar.pack_start(self.total_label)
        self.clean_btn = Gtk.Button(label="Tout nettoyer",
                                    css_classes=["suggested-action", "pill"])
        self.clean_btn.connect("clicked", self.on_clean_all)
        bar.pack_end(self.clean_btn)
        view.add_bottom_bar(bar)

        page.set_child(view)
        return page

    def on_simulate(self, action, value):
        action.set_state(value)
        self.simulating = value.get_boolean()
        self.sim_banner.set_revealed(self.simulating)
        self.clean_btn.set_label("Simuler le nettoyage" if self.simulating
                                 else "Tout nettoyer")
        self.toast("Mode simulation activé" if self.simulating
                   else "Mode simulation désactivé")

    def make_row(self, cid, row, search=False, switch=False, nav=False):
        row.set_use_markup(False)
        row.add_prefix(Gtk.Image(icon_name=ICONS[cid]))
        status = Status()
        row.add_suffix(status)
        self.status[cid] = status
        self.rows[cid] = row
        if cid in self.lists:
            status.size("—")
        if search:
            btn = Gtk.Button(label="Rechercher", valign=Gtk.Align.CENTER,
                             css_classes=["flat"])
            btn.connect("clicked", lambda *_: self.on_search(cid))
            row.add_suffix(btn)
        if switch:
            sw = Gtk.Switch(valign=Gtk.Align.CENTER,
                            active=self.settings["enabled"].get(cid, True))
            sw.connect("notify::active", self.on_switch, cid)
            row.add_suffix(sw)
        if nav:
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.set_activatable(True)
            row.connect("activated", lambda *_: self.open_list(cid))
        return row

    # ------------------------------------------------------------ estimates

    def refresh(self):
        if self.busy:
            return
        for cid in be.CATEGORIES:
            if cid == "orphans":
                continue
            self.status[cid].busy()
            in_background(be.estimate, self.on_estimate_cb(cid), cid,
                          dict(self.settings))
        if self.lists["orphans"] is not None:
            self.do_search("orphans")
        self.update_total()

    def on_estimate(self, cid, value):
        self.estimates[cid] = value
        self.status[cid].size("≈" if value is None else be.fmt_size(value))
        self.update_total()

    def update_total(self):
        total = 0
        for cid in be.CATEGORIES:
            if not self.settings["enabled"].get(cid, True):
                continue
            if cid == "orphans":
                total += self.selected_size("orphans")
            else:
                total += self.estimates.get(cid) or 0
        self.total_label.set_label(f"Place libérée estimée : {be.fmt_size(total)}")

    def selected_size(self, kind):
        data = self.lists[kind]
        if not data:
            return 0
        return sum(p["size"] for p in data["pkgs"] if p["name"] in data["checked"])

    def on_switch(self, sw, _pspec, cid):
        self.settings["enabled"][cid] = sw.get_active()
        be.save_settings(self.settings)
        self.update_total()

    def on_pacman_mode(self, radio, key, expander):
        if not radio.get_active():
            return
        self.settings["pacman_mode"] = key
        expander.set_subtitle(dict(be.PACMAN_MODES)[key])
        be.save_settings(self.settings)
        self.status["pacman"].busy()
        in_background(be.estimate, self.on_estimate_cb("pacman"),
                      "pacman", dict(self.settings))

    def on_journal_size(self, row, _pspec):
        self.settings["journal_mb"] = int(row.get_value())
        be.save_settings(self.settings)
        self.status["journal"].busy()
        in_background(be.estimate, self.on_estimate_cb("journal"),
                      "journal", dict(self.settings))

    def on_estimate_cb(self, cid):
        """in_background appelle done(résultat, erreur) : on garde le résultat."""
        return lambda value, _err: self.on_estimate(cid, value)

    # --------------------------------------------------------- package lists

    def on_search(self, kind, then=None):
        if kind != "explicit":
            self.do_search(kind, then)
            return
        dialog = Adw.AlertDialog(
            heading="Paquets installés explicitement",
            body=("Cette liste contient aussi les applis installées volontairement "
                  "(navigateur, applis maison…). Rien n'est coché par défaut : "
                  "vérifiez chaque paquet avant de le marquer comme dépendance."))
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("search", "Rechercher")
        dialog.set_response_appearance("search", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("search")
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _d, r: r == "search"
                       and self.do_search(kind, then))
        dialog.present(self)

    def do_search(self, kind, then=None):
        self.status[kind].busy()

        def done(pkgs, error):
            if error is not None:
                self.status[kind].done(False, str(error))
                self.toast(f"Recherche impossible : {error}")
                return
            previous = self.lists[kind]
            names = {p["name"] for p in pkgs}
            if kind == "orphans":
                checked = set(names)          # tout coché par défaut
            elif previous:
                checked = previous["checked"] & names
            else:
                checked = set()               # rien de coché par défaut
            self.lists[kind] = {"pkgs": pkgs, "checked": checked}
            self.update_list_row(kind)
            page = self.nav.find_page(kind)
            if page:
                page.rebuild()
            if then:
                then()

        in_background(be.search, done, kind)

    def update_list_row(self, kind):
        data = self.lists[kind]
        if data is None:
            return
        n = len(data["pkgs"])
        row = self.rows[kind]
        word = "dossier" if kind == "configs" else "paquet"
        if n == 0:
            row.set_subtitle(f"Aucun {word} trouvé")
        elif kind == "orphans":
            row.set_subtitle(f"{n} paquet{'s' if n > 1 else ''}, "
                             f"{len(data['checked'])} coché{'s' if len(data['checked']) > 1 else ''}")
        else:
            row.set_subtitle(f"{n} {word}{'s' if n > 1 else ''} à vérifier")
        size = (self.selected_size(kind) if kind == "orphans"
                else sum(p["size"] for p in data["pkgs"]))
        self.status[kind].size(be.fmt_size(size))
        self.update_total()

    def open_list(self, kind):
        def push():
            if not self.nav.find_page(kind):
                self.nav.push(PackagePage(self, kind))
        if self.lists[kind] is None:
            self.on_search(kind, then=push)
        else:
            push()

    def run_pkg_action(self, kind, names):
        if self.simulating:
            self.set_busy(True)

            def shown(result, error):
                self.set_busy(False)
                ok, message = result if result else (False, str(error))
                dialog = Adw.AlertDialog(
                    heading="Simulation" if ok else "Simulation : échec",
                    body=message)
                dialog.add_response("close", "Fermer")
                dialog.present(self)

            in_background(be.simulate_pkg_action, shown, kind, names)
            return
        if kind == "configs":
            self.set_busy(True)

            def trashed(result, error):
                self.set_busy(False)
                ok, message = result if result else (False, str(error))
                self.toast(message if ok else f"Échec : {message}")
                self.do_search("configs")

            in_background(be.trash_paths, trashed, names)
            return
        action = "asdeps" if kind == "explicit" else "remove"
        steps = [{"id": kind, "action": action, "packages": names}]
        self.set_busy(True)

        def done(result, error):
            self.set_busy(False)
            if error is not None:
                self.toast(str(error))
                return
            rc, results = result
            ok, message = results.get(kind, (False, be.helper_error(rc)))
            if not ok:
                self.toast(f"Échec : {message.splitlines()[-1] if message else ''}")
            elif action == "asdeps":
                self.toast("Marqués comme dépendances. Les orphelins ont été recherchés à nouveau.")
            else:
                self.toast(f"{len(names)} paquet{'s' if len(names) > 1 else ''} supprimé{'s' if len(names) > 1 else ''}")
            for k in ("orphans", "unneeded", "explicit"):
                if self.lists[k] is not None or k == "orphans":
                    self.do_search(k)

        in_background(be.run_helper, done, steps)

    # ------------------------------------------------------------ clean all

    def on_clean_all(self, *_):
        enabled = [c for c in be.CATEGORIES if self.settings["enabled"].get(c, True)]
        if not enabled:
            self.toast("Aucune catégorie activée")
            return
        if "orphans" in enabled and self.lists["orphans"] is None:
            self.do_search("orphans", then=self.on_clean_all)
            return

        if self.simulating:
            self.start_simulation(enabled)
            return

        lines = []
        for cid in enabled:
            detail = ""
            if cid == "orphans":
                n = len(self.lists["orphans"]["checked"])
                detail = f" : {n} paquet{'s' if n > 1 else ''}"
            elif cid == "pacman":
                detail = " : " + dict(be.PACMAN_MODES)[self.settings["pacman_mode"]].lower()
            elif cid == "journal":
                detail = f" : garder {self.settings['journal_mb']} Mo"
            lines.append(f"• {be.LABELS[cid]}{detail}")

        dialog = Adw.AlertDialog(
            heading="Tout nettoyer ?",
            body="\n".join(lines) + "\n\nLes opérations système demandent "
                 "votre mot de passe une seule fois.")
        dialog.add_response("cancel", "Annuler")
        dialog.add_response("clean", "Nettoyer")
        dialog.set_response_appearance("clean", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _d, r: r == "clean"
                       and self.start_clean(enabled))
        dialog.present(self)

    def start_clean(self, enabled):
        self.set_busy(True)
        for cid in enabled:
            self.status[cid].busy()

        settings = dict(self.settings)
        estimates = dict(self.estimates)
        orphan_names = (sorted(self.lists["orphans"]["checked"])
                        if "orphans" in enabled else [])
        orphan_bytes = self.selected_size("orphans") if orphan_names else 0

        def step_done(cid, ok, message=""):
            GLib.idle_add(lambda: self.status[cid].done(ok, message) and False)

        def work():
            report = {}
            before = {c: be.measure(c) for c in enabled if c != "orphans"}

            # 1. Opérations root, en un seul appel pkexec
            root = []
            if orphan_names:
                root.append({"id": "orphans", "action": "remove",
                             "packages": orphan_names})
            if "pacman" in enabled:
                root.append({"id": "pacman", "action": "pacman-cache",
                             "mode": settings["pacman_mode"]})
            if "aur" in enabled:
                pre = be.aur_precheck()
                if pre is None:
                    root.append({"id": "aur", "action": "shelly-aur-cache"})
                else:
                    report["aur"] = pre
                    step_done("aur", *pre)
            if "fwupd" in enabled:
                root.append({"id": "fwupd", "action": "fwupd-cache"})
            if "journal" in enabled:
                root.append({"id": "journal", "action": "journal",
                             "size_mb": settings["journal_mb"]})
            if root:
                rc, results = be.run_helper(
                    root, on_line=lambda item: step_done(
                        item.get("id"), item.get("ok"), item.get("message", "")))
                for step in root:
                    ok, message = results.get(step["id"], (False, be.helper_error(rc)))
                    report[step["id"]] = (ok, message)
                    if step["id"] not in results:
                        step_done(step["id"], False, message)
            if "orphans" in enabled and not orphan_names:
                report["orphans"] = (True, "Aucun paquet sélectionné")
                step_done("orphans", True)

            # 2. Opérations utilisateur, dans l'ordre de l'ancienne fonction
            reported = {}
            for cid in ("browsers", "webcache", "flatpak", "home",
                        "shaders", "dev", "containers"):
                if cid in enabled:
                    try:
                        ok, message, *size = be.USER_CLEANERS[cid]()
                        if size:
                            reported[cid] = size[0]
                    except OSError as exc:
                        ok, message = False, str(exc)
                    report[cid] = (ok, message)
                    step_done(cid, ok, message)

            # 3. Place réellement libérée, et vérification
            freed = {}
            for cid in enabled:
                if cid == "orphans":
                    freed[cid] = orphan_bytes if report.get("orphans", (False,))[0] else 0
                    continue
                if cid in reported:
                    freed[cid] = reported[cid]
                    continue
                after = be.measure(cid)
                freed[cid] = max(0, (before.get(cid) or 0) - (after or 0))
                expected = estimates.get(cid) or 0
                ok, message = report.get(cid, (False, ""))
                if ok and cid != "browsers" and expected > 1_000_000 and freed[cid] == 0:
                    report[cid] = (False, "La commande a réussi mais rien n'a été "
                                          f"libéré (attendu : {be.fmt_size(expected)}). "
                                          + message)
                    step_done(cid, False, report[cid][1])
            return report, freed

        def done(result, error):
            self.set_busy(False)
            if error is not None:
                self.toast(f"Nettoyage interrompu : {error}")
                self.refresh()
                return
            report, freed = result
            self.show_recap(enabled, report, freed)

        in_background(work, done)

    def start_simulation(self, enabled):
        self.set_busy(True)
        for cid in enabled:
            self.status[cid].busy()
        settings = dict(self.settings)
        packages = (sorted(self.lists["orphans"]["checked"])
                    if "orphans" in enabled else [])

        def work():
            report, freed = {}, {}
            for cid in enabled:
                ok, message, size = be.simulate(cid, settings, packages)
                report[cid], freed[cid] = (ok, message), size
                GLib.idle_add(lambda c=cid, o=ok, m=message:
                              self.status[c].done(o, m) and False)
            return report, freed

        def done(result, error):
            self.set_busy(False)
            if error is not None:
                self.toast(f"Simulation interrompue : {error}")
                self.refresh()
                return
            report, freed = result
            self.show_recap(enabled, report, freed, simulated=True)

        in_background(work, done)

    def show_recap(self, enabled, report, freed, simulated=False):
        total = sum(freed.values())
        failures = [c for c in enabled if not report.get(c, (False,))[0]]

        dialog = Adw.Dialog(title="Simulation" if simulated else "Récapitulatif",
                            content_width=460, content_height=560)
        view = Adw.ToolbarView()
        view.add_top_bar(Adw.HeaderBar())
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(
            title=(f"Place qui serait libérée : {be.fmt_size(total)}" if simulated
                   else f"Place libérée : {be.fmt_size(total)}"),
            description=("Rien n'a été supprimé ni modifié." if simulated and not failures
                         else "Nettoyage terminé." if not failures else
                         f"{len(failures)} opération{'s' if len(failures) > 1 else ''} "
                         "en échec : survolez l'icône pour le détail."))
        for cid in enabled:
            ok, message = report.get(cid, (False, "Non exécuté"))
            row = Adw.ActionRow(title=be.LABELS[cid], use_markup=False,
                                subtitle=(message.splitlines()[-1][:160]
                                          if message else ""),
                                subtitle_lines=3, tooltip_text=message or None)
            row.add_prefix(Gtk.Image(icon_name=ICONS[cid]))
            if ok:
                text = ("≈" if cid in ("browsers", "flatpak", "containers") and not freed.get(cid)
                        else be.fmt_size(freed.get(cid, 0)))
                row.add_suffix(Gtk.Label(label=text, css_classes=["numeric"]))
            else:
                row.add_suffix(Gtk.Image(icon_name="dialog-warning-symbolic",
                                         css_classes=["warning"],
                                         tooltip_text=message or None))
            group.add(row)
        page.add(group)
        view.set_content(page)
        dialog.set_child(view)
        dialog.connect("closed", lambda *_: self.refresh())
        dialog.present(self)

    # ---------------------------------------------------------------- misc

    def set_busy(self, busy):
        self.busy = busy
        self.clean_btn.set_sensitive(not busy)
        self.refresh_btn.set_sensitive(not busy)
        for kind in self.lists:
            page = self.nav.find_page(kind)
            if page:
                page.update_selection()

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text),
                                        timeout=5))
