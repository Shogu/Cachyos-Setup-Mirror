#!/usr/bin/env python3
"""Icônes Ogu — remet mes icônes maison (couleur + symboliques) sur un GNOME.

Un seul fichier autonome (icones-ogu.pyz) qui embarque toute la collection.
Les icônes importées vont dans ~/.local/share/icones-ogu/importees et passent devant celles
embarquées ; « Exporter » recrée un .pyz qui les contient.

Colonnes : appli | icônes actuelles | icônes proposées | import.
Menu Actions : appliquer, restaurer, remettre mes lanceurs faits main, exporter la collection,
fermer la session. Chaque action demande confirmation.
"""
import configparser
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
THEME = DATA / "icons/hicolor"
USER_APPS = DATA / "applications"
STATE = DATA / "icones-ogu"
IMPORTED = STATE / "importees"
SNAPSHOTS = STATE / "instantanes"
APP_DIRS = [USER_APPS, DATA / "flatpak/exports/share/applications",
            Path("/var/lib/flatpak/exports/share/applications"),
            Path("/usr/local/share/applications"), Path("/usr/share/applications")]
HERE = Path(__file__).resolve().parent
BUNDLE = Path(os.environ.get("ICONES_OGU_DIR", HERE))      # icones.sh, icones/, lanceurs/
SIZE = 48


# ---------------------------------------------------------------- données

def launchers():
    """{id: chemin du .desktop visible} — la copie perso masque la copie système."""
    seen = {}
    for d in APP_DIRS:
        for f in sorted(d.glob("*.desktop")) if d.is_dir() else []:
            seen.setdefault(f.stem, f)
    return seen


def desktop_field(path, key):
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    try:
        cp.read(path, encoding="utf-8")
        return cp.get("Desktop Entry", key, fallback="")
    except Exception:
        return ""


def scan(folder, found, origin):
    if not Path(folder).is_dir():
        return
    for f in sorted(Path(folder).rglob("*")):
        if f.suffix not in (".svg", ".png") or not f.is_file():
            continue
        name, kind = f.stem, "color"
        if name.endswith("-symbolic"):
            name, kind = name[: -len("-symbolic")], "symbolic"
        e = found.setdefault(name, {"color": None, "symbolic": None, "imported": set()})
        prev = e[kind]
        # un import remplace le paquet ; à origine égale, le SVG passe devant le PNG
        if prev is None or origin == "import" or (f.suffix == ".svg" and kind not in e["imported"]):
            e[kind] = f
            if origin == "import":
                e["imported"].add(kind)


def collection():
    found = {}
    scan(BUNDLE / "icones", found, "paquet")
    scan(IMPORTED, found, "import")
    return found


def digest(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def theme_files(ident):
    """Fichiers de ton thème qui portent exactement ce nom (couleur, PNG de toutes tailles, symbolique)."""
    return [f for f in THEME.glob("*/apps/*") if f.stem in (ident, ident + "-symbolic")]


def refresh_caches():
    for cmd in (["gtk-update-icon-cache", "-q", "-f", "-t", str(THEME)],
                ["update-desktop-database", "-q", str(USER_APPS)]):
        try:
            subprocess.run(cmd, check=False, capture_output=True)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------- instantanés

def snapshot(ids):
    """Copie, avant modification, tout ce qui porte ces noms dans ton thème et tes lanceurs."""
    dest = SNAPSHOTS / datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    manifest = {"ids": sorted(ids), "files": [], "launchers": {}}
    for i in ids:
        for f in theme_files(i):
            rel = f.relative_to(THEME)
            (dest / "icons" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest / "icons" / rel)
            manifest["files"].append(str(rel))
        lf = USER_APPS / f"{i}.desktop"
        manifest["launchers"][i] = lf.is_file()
        if lf.is_file():
            (dest / "applications").mkdir(parents=True, exist_ok=True)
            shutil.copy2(lf, dest / "applications" / lf.name)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "manifeste.json").write_text(json.dumps(manifest, indent=1))
    return dest


def restore(dest):
    m = json.loads((dest / "manifeste.json").read_text())
    for i in m["ids"]:
        for f in theme_files(i):
            f.unlink()
        lf = USER_APPS / f"{i}.desktop"
        if m["launchers"].get(i):
            shutil.copy2(dest / "applications" / lf.name, lf)
        elif lf.exists():
            lf.unlink()       # lanceur créé par l'application : on le retire
    for rel in m["files"]:
        (THEME / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest / "icons" / rel, THEME / rel)
    refresh_caches()
    return len(m["ids"])


def build_pyz(out):
    """Nouveau fichier autonome : l'appli + la collection actuelle (paquet + imports) + lanceurs."""
    import zipfile
    out = Path(out)
    with open(out, "wb") as f:
        f.write(b"#!/usr/bin/env python3\n")
        with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(BUNDLE / "__main__.py", "__main__.py")
            for name in ("__main__.py", "icones-ogu.py", "icones.sh"):
                z.write(BUNDLE / name, f"bundle/{name}")
            for ident, c in sorted(collection().items()):
                for kind, suffix in (("color", ""), ("symbolic", "-symbolic")):
                    if c[kind]:
                        z.write(c[kind], f"bundle/icones/{ident}{suffix}{c[kind].suffix}")
            for lf in sorted((BUNDLE / "lanceurs").glob("*.desktop")):
                z.write(lf, f"bundle/lanceurs/{lf.name}")
    out.chmod(0o755)
    return out


# ---------------------------------------------------------------- interface

class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Icônes Ogu")
        self.set_default_size(1180, 780)
        self.rows = []      # (id, check)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(8)
        self.set_child(box)

        bar = Gtk.Box(spacing=6)
        box.append(bar)
        for label, cb in (("Importer des icônes…", self.on_import_files),
                          ("Actualiser", lambda *_: self.reload()),
                          ("Tout cocher", lambda *_: self.check_all(True)),
                          ("Tout décocher", lambda *_: self.check_all(False))):
            b = Gtk.Button(label=label)
            b.connect("clicked", cb)
            bar.append(b)
        self.show_all = Gtk.CheckButton(label="Afficher toutes les applis installées")
        self.show_all.connect("toggled", lambda *_: self.reload())
        bar.append(self.show_all)
        bar.append(Gtk.Box(hexpand=True))
        menu = Gio.Menu()
        menu.append("Appliquer les nouvelles icônes (cochées)…", "win.apply")
        menu.append("Restaurer les anciennes icônes…", "win.restore")
        menu.append("Remettre mes lanceurs faits main…", "win.launchers")
        menu.append("Exporter (nouveau fichier avec mes imports)…", "win.export")
        menu.append("Recharger la session GNOME (déconnexion)…", "win.logout")
        bar.append(Gtk.MenuButton(label="Actions", menu_model=menu))
        for name, cb in (("apply", self.on_apply), ("restore", self.on_restore),
                         ("launchers", self.on_launchers), ("export", self.on_export),
                         ("logout", self.on_logout)):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)

        self.status = Gtk.Label(xalign=0, wrap=True)
        box.append(self.status)

        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        box.append(paned)
        sc = Gtk.ScrolledWindow(vexpand=True)
        self.grid = Gtk.Grid(column_spacing=14, row_spacing=6)
        sc.set_child(self.grid)
        paned.set_start_child(sc)
        self.log = Gtk.TextView(editable=False, monospace=True)
        lsc = Gtk.ScrolledWindow(min_content_height=130)
        lsc.set_child(self.log)
        paned.set_end_child(lsc)
        paned.set_position(560)

        self.reload()

    # ----- affichage
    def write(self, text):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), text.rstrip() + "\n")
        self.log.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 0)

    def image_from_file(self, path):
        img = Gtk.Image.new_from_file(str(path))
        img.set_pixel_size(SIZE)
        img.set_tooltip_text(str(path))
        return img

    def missing(self, text):
        lab = Gtk.Label(label=text)
        lab.add_css_class("dim-label")
        lab.set_size_request(SIZE, SIZE)
        return lab

    def current_image(self, name):
        """Ce que GTK affiche aujourd'hui pour ce nom (ou ce chemin), + le fichier retenu."""
        if not name:
            return self.missing("aucune"), None
        if name.startswith("/"):
            return (self.image_from_file(name), name) if Path(name).is_file() else (self.missing("introuvable"), None)
        theme = Gtk.IconTheme.get_for_display(self.get_display())
        if not theme.has_icon(name):
            return self.missing("aucune"), None
        p = theme.lookup_icon(name, None, SIZE, 1, Gtk.TextDirection.NONE, 0)
        f = p.get_file()
        path = f.get_path() if f else None
        img = Gtk.Image.new_from_paintable(p)
        img.set_pixel_size(SIZE)
        img.set_tooltip_text(path or name)
        return img, path

    def reload(self):
        while (child := self.grid.get_first_child()) is not None:
            self.grid.remove(child)
        self.rows = []
        script = BUNDLE / "icones.sh"
        apps = launchers()
        coll = collection()
        absent = sum(1 for k in coll if k not in apps)
        nimp = sum(1 for v in coll.values() if v["imported"])
        self.status.set_text(
            f"Collection : {len(coll)} appli(s) dont {nimp} avec import perso · "
            f"{absent} ignorée(s) car non installée(s)"
            + ("" if script.is_file() else f"\n⚠ icones.sh introuvable dans {BUNDLE}"))
        for col, t in enumerate(("", "Appli", "Couleur actuelle", "Symbolique actuelle",
                                 "Couleur proposée", "Symbolique proposée", "Importer", "")):
            lab = Gtk.Label(xalign=0)
            lab.set_markup(f"<b>{t}</b>")
            self.grid.attach(lab, col, 0, 1, 1)

        ids = [k for k in coll if k in apps]
        if self.show_all.get_active():
            ids += [k for k in apps if k not in coll and desktop_field(apps[k], "NoDisplay") != "true"]
        name_of = {k: desktop_field(apps[k], "Name") or k for k in ids}
        for r, ident in enumerate(sorted(ids, key=lambda k: name_of[k].lower()), start=1):
            c = coll.get(ident, {"color": None, "symbolic": None, "imported": set()})
            icon = desktop_field(apps[ident], "Icon")
            cur_c, cur_c_path = self.current_image(icon)
            cur_s, cur_s_path = self.current_image(f"{icon}-symbolic" if icon and not icon.startswith("/") else "")
            has = c["color"] or c["symbolic"]
            same = has and ((c["color"] is None or (cur_c_path and digest(cur_c_path) == digest(c["color"]))) and
                            (c["symbolic"] is None or (cur_s_path and digest(cur_s_path) == digest(c["symbolic"]))))
            check = Gtk.CheckButton(active=bool(has) and not same, sensitive=bool(has))
            self.rows.append((ident, check))
            lab = Gtk.Label(xalign=0)
            lab.set_markup(f"<b>{GLib.markup_escape_text(name_of[ident])}</b>\n"
                           f"<small>{GLib.markup_escape_text(ident)}</small>")
            notes = []
            if same:
                notes.append("déjà en place")
            elif icon.startswith("/") and has:
                notes.append("Icon= est un chemin : sera remplacé par le nom")
            if c["imported"]:
                notes.append("import perso : " + " + ".join(sorted("couleur" if k == "color" else "symbolique"
                                                                   for k in c["imported"])))
            self.grid.attach(check, 0, r, 1, 1)
            self.grid.attach(lab, 1, r, 1, 1)
            self.grid.attach(cur_c, 2, r, 1, 1)
            self.grid.attach(cur_s, 3, r, 1, 1)
            self.grid.attach(self.image_from_file(c["color"]) if c["color"] else self.missing("—"), 4, r, 1, 1)
            self.grid.attach(self.image_from_file(c["symbolic"]) if c["symbolic"] else self.missing("—"), 5, r, 1, 1)
            ib = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
            for label, kind in (("Couleur…", "color"), ("Symbolique…", "symbolic")):
                b = Gtk.Button(label=label)
                b.connect("clicked", self.on_import_one, ident, kind)
                ib.append(b)
            if c["imported"]:
                b = Gtk.Button(label="Oublier l'import")
                b.connect("clicked", self.on_forget, ident)
                ib.append(b)
            self.grid.attach(ib, 6, r, 1, 1)
            self.grid.attach(Gtk.Label(label=" · ".join(notes), xalign=0), 7, r, 1, 1)

    def check_all(self, value):
        for _, c in self.rows:
            if c.get_sensitive():
                c.set_active(value)

    # ----- confirmations
    def confirm(self, message, detail, ok, callback):
        d = Gtk.AlertDialog(message=message, detail=detail, buttons=["Annuler", ok],
                            cancel_button=0, default_button=0, modal=True)

        def done(dlg, res):
            try:
                if dlg.choose_finish(res) == 1:
                    callback()
            except GLib.Error:
                pass
        d.choose(self, None, done)

    def image_filter(self):
        f = Gtk.FileFilter(name="Images SVG / PNG")
        for p in ("*.svg", "*.png"):
            f.add_pattern(p)
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f)
        return store

    # ----- imports
    def on_import_one(self, _btn, ident, kind):
        fd = Gtk.FileDialog(title=f"{'Symbolique' if kind == 'symbolic' else 'Icône couleur'} pour {ident}",
                            filters=self.image_filter())

        def done(dlg, res):
            try:
                src = Path(dlg.open_finish(res).get_path())
            except GLib.Error:
                return
            if kind == "symbolic" and src.suffix != ".svg":
                self.write("Une symbolique doit être un SVG.")
                return
            IMPORTED.mkdir(parents=True, exist_ok=True)
            stem = ident + ("-symbolic" if kind == "symbolic" else "")
            for old in IMPORTED.glob(stem + ".*"):
                old.unlink()
            shutil.copy2(src, IMPORTED / f"{stem}{src.suffix}")
            self.write(f"Importé : {src.name} → {stem}{src.suffix} (pas encore appliqué)")
            self.reload()
        fd.open(self, None, done)

    def on_import_files(self, *_):
        fd = Gtk.FileDialog(title="Importer des icônes nommées NOM.svg / NOM.png / NOM-symbolic.svg",
                            filters=self.image_filter())

        def done(dlg, res):
            try:
                files = dlg.open_multiple_finish(res)
            except GLib.Error:
                return
            apps = launchers()
            IMPORTED.mkdir(parents=True, exist_ok=True)
            for i in range(files.get_n_items()):
                src = Path(files.get_item(i).get_path())
                base = src.stem[: -len("-symbolic")] if src.stem.endswith("-symbolic") else src.stem
                shutil.copy2(src, IMPORTED / src.name)
                self.write(f"Importé : {src.name}" + ("" if base in apps else
                           f"  ⚠ aucune appli « {base} » : renomme le fichier comme le lanceur, "
                           "ou utilise les boutons Couleur… / Symbolique… de la bonne ligne"))
            self.reload()
        fd.open_multiple(self, None, done)

    def on_forget(self, _btn, ident):
        for f in IMPORTED.glob("*"):
            if f.stem in (ident, ident + "-symbolic"):
                f.unlink()
        self.write(f"{ident} : retour aux icônes d'origine (pas encore appliqué)")
        self.reload()

    # ----- actions
    def on_apply(self, *_):
        ids = [i for i, c in self.rows if c.get_active()]
        if not ids:
            self.write("Rien de coché.")
            return
        detail = (f"{len(ids)} appli(s) : " + ", ".join(ids[:12]) + (" …" if len(ids) > 12 else "") +
                  "\n\nUn instantané de l'état actuel est pris avant : « Restaurer les anciennes "
                  "icônes » remettra tout comme maintenant. Rien n'est modifié dans /usr.")
        self.confirm("Appliquer les nouvelles icônes ?", detail, "Appliquer", lambda: self.do_apply(ids))

    def do_apply(self, ids):
        snap = snapshot(ids)
        self.write(f"Instantané : {snap}")
        coll = collection()
        with tempfile.TemporaryDirectory() as tmp:
            for i in ids:
                for kind, suffix in (("color", ""), ("symbolic", "-symbolic")):
                    src = coll[i][kind]
                    if src:
                        shutil.copy2(src, Path(tmp) / f"{i}{suffix}{src.suffix}")
            res = subprocess.run(["bash", str(BUNDLE / "icones.sh"), "appliquer", tmp],
                                 capture_output=True, text=True)
        self.write(res.stdout + res.stderr)
        self.write("Fait. Pour voir le résultat partout : Actions → Recharger la session GNOME.")
        self.reload()

    def on_restore(self, *_):
        snaps = sorted(SNAPSHOTS.glob("*/manifeste.json"), reverse=True) if SNAPSHOTS.is_dir() else []
        if not snaps:
            self.write("Aucun instantané : rien n'a encore été appliqué depuis cette fenêtre.")
            return
        dest = snaps[0].parent
        m = json.loads(snaps[0].read_text())
        detail = (f"Instantané du {dest.name.replace('_', ' à ')} ({len(m['ids'])} appli(s)).\n\n"
                  "Les icônes de ces applis reviennent à leur état d'avant le dernier « Appliquer ». "
                  "Les autres ne sont pas touchées. On peut recommencer pour remonter plus loin.")
        self.confirm("Restaurer les anciennes icônes ?", detail, "Restaurer", lambda: self.do_restore(dest))

    def do_restore(self, dest):
        n = restore(dest)
        dest.rename(dest.with_name(dest.name + "-restaure"))
        self.write(f"{n} appli(s) remise(s) dans l'état d'avant ({dest.name}).")
        self.reload()

    def on_launchers(self, *_):
        src = BUNDLE / "lanceurs"
        todo = [f for f in sorted(src.glob("*.desktop"))] if src.is_dir() else []
        todo = [f for f in todo if not (USER_APPS / f.name).exists()]
        if not todo:
            self.write("Lanceurs faits main : tous déjà en place.")
            return
        detail = (f"{len(todo)} lanceur(s) absent(s) d'ici : " + ", ".join(f.stem for f in todo[:15]) +
                  (" …" if len(todo) > 15 else "") +
                  "\n\nIls sont copiés dans ~/.local/share/applications. Ceux déjà présents ne sont pas touchés.")

        def go():
            USER_APPS.mkdir(parents=True, exist_ok=True)
            for f in todo:
                shutil.copy2(f, USER_APPS / f.name)
            refresh_caches()
            self.write(f"{len(todo)} lanceur(s) remis en place.")
            self.reload()
        self.confirm("Remettre mes lanceurs faits main ?", detail, "Remettre", go)

    def on_export(self, *_):
        out = HOME / f"icones-ogu-{datetime.date.today()}.pyz"
        n = len(collection())
        self.confirm("Exporter ma collection ?",
                     f"Crée {out.name} dans ton dossier personnel : cette même appli, avec les {n} "
                     "icônes actuelles (celles d'origine + tes imports) et tes lanceurs faits main. "
                     "C'est ce fichier-là qu'il faut garder (dépôt GitLab, clé USB…).",
                     "Exporter", lambda: self.write(f"Exporté → {build_pyz(out)}"))

    def on_logout(self, *_):
        self.confirm("Fermer la session GNOME ?",
                     "Sous Wayland, GNOME Shell ne peut pas être relancé seul : il faut fermer la "
                     "session et se reconnecter.\n\nEnregistre ton travail dans les autres applis avant.",
                     "Fermer la session",
                     lambda: subprocess.Popen(["gnome-session-quit", "--logout", "--no-prompt"]))


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.gitlab.shogu.IconesOgu")

    def do_activate(self):
        (self.get_active_window() or Window(self)).present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
