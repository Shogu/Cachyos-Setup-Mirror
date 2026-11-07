#!/usr/bin/env python3
"""Dossiers Ogu — crée mes dossiers, leur met leurs icônes, masque ceux que je n'utilise pas.

Un seul fichier autonome (dossiers-ogu.pyz) qui embarque :
  plan.json   la liste des dossiers (chemin depuis ~, icône, à créer ou non) et ceux à masquer
  icones/     les icônes des dossiers que j'utilise (dossier-xxx.svg)

Ces icônes sont recopiées dans ~/.local/share/dossiers-ogu/icones : c'est là que pointent les icônes
des dossiers (attribut metadata::custom-icon lu par Fichiers). Mes changements de plan et mes
imports y restent ; « Exporter » recrée un .pyz qui les contient.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
STATE = DATA / "dossiers-ogu"
RESERVE = STATE / "icones"
USER_PLAN = STATE / "plan.json"
SNAPSHOTS = STATE / "instantanes"
BUNDLE = Path(os.environ.get("DOSSIERS_OGU_DIR", Path(__file__).resolve().parent))
USER_DIRS = CONFIG / "user-dirs.dirs"
ATTR = "metadata::custom-icon"
SIZE = 56


# ---------------------------------------------------------------- données

def sync_reserve():
    """Recopie les icônes embarquées (sans écraser un import du même nom)."""
    RESERVE.mkdir(parents=True, exist_ok=True)
    for f in (BUNDLE / "icones").glob("*"):
        dst = RESERVE / f.name
        if not dst.exists():
            shutil.copy2(f, dst)


def load_plan():
    src = USER_PLAN if USER_PLAN.is_file() else BUNDLE / "plan.json"
    return json.loads(src.read_text(encoding="utf-8"))


def save_plan(plan):
    STATE.mkdir(parents=True, exist_ok=True)
    USER_PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def reserve_icons():
    return sorted(p for p in RESERVE.glob("*") if p.suffix in (".svg", ".png"))


def icon_file(name):
    if not name:
        return None
    for ext in (".svg", ".png"):
        p = RESERVE / f"{name}{ext}"
        if p.is_file():
            return p
    return None


def custom_icon(path):
    """Valeur actuelle de metadata::custom-icon (URI) ou None."""
    try:
        info = Gio.File.new_for_path(str(path)).query_info(ATTR, Gio.FileQueryInfoFlags.NONE, None)
        return info.get_attribute_string(ATTR)
    except GLib.Error:
        return None


def set_custom_icon(path, uri):
    """Pose (ou efface si uri est None) l'icône perso, comme « gio set » — lu par Fichiers."""
    cmd = (["gio", "set", str(path), ATTR, uri] if uri else ["gio", "set", "-t", "unset", str(path), ATTR])
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise GLib.Error((res.stderr or res.stdout).strip() or "gio set a échoué")


# ----- dossiers masqués (renommés en .Nom, comme .Bureau) + user-dirs.dirs

def read_user_dirs():
    lines = USER_DIRS.read_text(encoding="utf-8").splitlines() if USER_DIRS.is_file() else []
    return lines


def xdg_key_for(name, lines):
    for ln in lines:
        m = re.match(r'^(XDG_\w+_DIR)="\$HOME/(.+)"$', ln.strip())
        if m and m.group(2) in (name, "." + name):
            return m.group(1)
    return None


def hide_folder(name):
    """Renomme ~/Nom en ~/.Nom et met user-dirs.dirs à jour. Renvoie un message."""
    src, dst = HOME / name, HOME / ("." + name)
    lines = read_user_dirs()
    key = xdg_key_for(name, lines)
    if src.exists() and dst.exists():
        return f"{name} : « {name} » et « .{name} » existent tous les deux, à régler à la main"
    if src.exists():
        src.rename(dst)
    elif not dst.exists():
        dst.mkdir(parents=True)
    if key:
        new = [f'{key}="$HOME/.{name}"' if ln.strip().startswith(key + "=") else ln for ln in lines]
        USER_DIRS.write_text("\n".join(new) + "\n", encoding="utf-8")
        return f"{name} → .{name} (et {key} mis à jour)"
    return f"{name} → .{name}"


def unhide_folder(name):
    src, dst = HOME / ("." + name), HOME / name
    lines = read_user_dirs()
    key = xdg_key_for(name, lines)
    if src.exists() and not dst.exists():
        src.rename(dst)
    if key:
        new = [f'{key}="$HOME/{name}"' if ln.strip().startswith(key + "=") else ln for ln in lines]
        USER_DIRS.write_text("\n".join(new) + "\n", encoding="utf-8")


# ----- instantanés

def snapshot(rows, hidden):
    dest = SNAPSHOTS / datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest.mkdir(parents=True, exist_ok=True)
    data = {"icones": {}, "existaient": {}, "masques": {}}
    for chemin in rows:
        p = HOME / chemin
        data["existaient"][chemin] = p.exists()
        data["icones"][chemin] = custom_icon(p) if p.exists() else None
    for name in hidden:
        data["masques"][name] = ("visible" if (HOME / name).exists() else
                                 "masque" if (HOME / ("." + name)).exists() else "absent")
    if USER_DIRS.is_file():
        shutil.copy2(USER_DIRS, dest / "user-dirs.dirs")
    (dest / "instantane.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest


def restore(dest):
    data = json.loads((dest / "instantane.json").read_text(encoding="utf-8"))
    log = []
    for name, before in data["masques"].items():
        dot = HOME / ("." + name)
        if before == "visible" and dot.exists():
            unhide_folder(name)
            log.append(f"{name} : de nouveau visible")
        elif before == "absent" and dot.is_dir():
            try:
                dot.rmdir()
                log.append(f".{name} : dossier vide retiré")
            except OSError:
                pass
    if (dest / "user-dirs.dirs").is_file():
        shutil.copy2(dest / "user-dirs.dirs", USER_DIRS)
    for chemin, uri in data["icones"].items():
        p = HOME / chemin
        if not p.exists():
            continue
        try:
            set_custom_icon(p, uri)
            log.append(f"{chemin} : icône remise")
        except GLib.Error as e:
            log.append(f"{chemin} : {e.message}")
        if not data["existaient"].get(chemin, True):
            try:
                p.rmdir()       # créé par l'appli et toujours vide : on le retire
                log.append(f"{chemin} : dossier vide retiré")
            except OSError:
                pass
    return log


def build_pyz(out):
    out = Path(out)
    with open(out, "wb") as f:
        f.write(b"#!/usr/bin/env python3\n")
        with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(BUNDLE / "__main__.py", "__main__.py")
            for name in ("__main__.py", "dossiers-ogu.py", "correspondances.txt"):
                if (BUNDLE / name).is_file():
                    z.write(BUNDLE / name, f"bundle/{name}")
            z.writestr("bundle/plan.json", json.dumps(load_plan(), ensure_ascii=False, indent=1))
            for p in reserve_icons():
                z.write(p, f"bundle/icones/{p.name}")
    out.chmod(0o755)
    return out


# ---------------------------------------------------------------- interface

class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Dossiers Ogu")
        self.set_default_size(1150, 800)
        self.plan = load_plan()
        self.rows = []      # (genre, clé, check)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(8)
        self.set_child(box)

        bar = Gtk.Box(spacing=6)
        box.append(bar)
        for label, cb in (("Ajouter un dossier…", self.on_add),
                          ("Importer des icônes…", self.on_import),
                          ("Actualiser", lambda *_: self.reload()),
                          ("Tout cocher", lambda *_: self.check_all(True)),
                          ("Tout décocher", lambda *_: self.check_all(False))):
            b = Gtk.Button(label=label)
            b.connect("clicked", cb)
            bar.append(b)
        bar.append(Gtk.Box(hexpand=True))
        menu = Gio.Menu()
        menu.append("Appliquer (cochés)…", "win.apply")
        menu.append("Restaurer l'état d'avant…", "win.restore")
        menu.append("Exporter (nouveau fichier avec mes changements)…", "win.export")
        menu.append("Relancer Fichiers…", "win.nautilus")
        bar.append(Gtk.MenuButton(label="Actions", menu_model=menu))
        for name, cb in (("apply", self.on_apply), ("restore", self.on_restore),
                         ("export", self.on_export), ("nautilus", self.on_nautilus)):
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
        lsc = Gtk.ScrolledWindow(min_content_height=120)
        lsc.set_child(self.log)
        paned.set_end_child(lsc)
        paned.set_position(600)
        self.reload()

    # ----- affichage
    def write(self, text):
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), text.rstrip() + "\n")
        self.log.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 0)

    def pic(self, path, tip=None):
        img = Gtk.Image.new_from_file(str(path))
        img.set_pixel_size(SIZE)
        img.set_tooltip_text(tip or Path(path).name)
        return img

    def text(self, t, dim=True):
        lab = Gtk.Label(label=t)
        if dim:
            lab.add_css_class("dim-label")
        lab.set_size_request(SIZE, SIZE)
        return lab

    def current_widget(self, path):
        if not path.exists():
            return self.text("absent")
        uri = custom_icon(path)
        if uri:
            fp = Gio.File.new_for_uri(uri).get_path()
            if fp and Path(fp).is_file():
                return self.pic(fp, fp)
            return self.text("icône\nintrouvable")
        try:
            info = Gio.File.new_for_path(str(path)).query_info("standard::icon", Gio.FileQueryInfoFlags.NONE, None)
            img = Gtk.Image.new_from_gicon(info.get_icon())
            img.set_pixel_size(SIZE)
            img.set_tooltip_text("icône standard")
            return img
        except GLib.Error:
            return self.text("—")

    def reload(self):
        while (c := self.grid.get_first_child()) is not None:
            self.grid.remove(c)
        self.rows = []
        n_res = len(reserve_icons())
        self.status.set_text(f"{n_res} icône(s) dans {RESERVE} · plan : "
                             f"{'le tien (modifié)' if USER_PLAN.is_file() else 'celui du fichier'}")
        for col, t in enumerate(("", "Dossier", "Actuelle", "Proposée", "", "")):
            lab = Gtk.Label(xalign=0)
            lab.set_markup(f"<b>{t}</b>")
            self.grid.attach(lab, col, 0, 1, 1)
        r = 1
        for entry in self.plan["dossiers"]:
            chemin, icone = entry["chemin"], entry.get("icone")
            p = HOME / chemin
            target = icon_file(icone)
            cur = custom_icon(p) if p.exists() else None
            same = (target and cur == target.as_uri()) or (not icone and not cur and p.exists())
            check = Gtk.CheckButton(active=not same and (p.exists() or bool(entry.get("creer"))))
            self.rows.append(("dossier", chemin, check))
            lab = Gtk.Label(xalign=0)
            lab.set_markup(f"<b>~/{GLib.markup_escape_text(chemin)}</b>\n<small>"
                           + ("créé s'il manque" if entry.get("creer") else "pas créé (Dropbox le fait)")
                           + "</small>")
            self.grid.attach(check, 0, r, 1, 1)
            self.grid.attach(lab, 1, r, 1, 1)
            self.grid.attach(self.current_widget(p), 2, r, 1, 1)
            if target:
                self.grid.attach(self.pic(target), 3, r, 1, 1)
            else:
                self.grid.attach(self.text("standard" if not icone else f"{icone}\nabsente"), 3, r, 1, 1)
            btns = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
            pick = Gtk.MenuButton(label="Choisir…")
            pick.set_popover(self.picker(entry))
            btns.append(pick)
            for label, cb in (("Standard", lambda _b, e=entry: self.set_icon(e, None)),
                              ("Retirer la ligne", lambda _b, e=entry: self.remove_row(e))):
                b = Gtk.Button(label=label)
                b.connect("clicked", cb)
                btns.append(b)
            self.grid.attach(btns, 4, r, 1, 1)
            note = "déjà en place" if same else ("absent : sera créé" if not p.exists() and entry.get("creer")
                                                 else "absent : ignoré" if not p.exists() else "")
            self.grid.attach(Gtk.Label(label=note, xalign=0), 5, r, 1, 1)
            r += 1

        sep = Gtk.Label(xalign=0)
        sep.set_markup("\n<b>Dossiers à masquer</b> (renommés en .Nom, comme .Bureau ; user-dirs.dirs suit)")
        self.grid.attach(sep, 0, r, 6, 1)
        r += 1
        for name in self.plan.get("masques", []):
            hidden = (HOME / ("." + name)).exists() and not (HOME / name).exists()
            check = Gtk.CheckButton(active=not hidden)
            self.rows.append(("masque", name, check))
            lab = Gtk.Label(xalign=0)
            lab.set_markup(f"<b>~/{GLib.markup_escape_text(name)}</b>")
            self.grid.attach(check, 0, r, 1, 1)
            self.grid.attach(lab, 1, r, 1, 1)
            self.grid.attach(self.text("masqué" if hidden else "visible" if (HOME / name).exists() else "absent", False), 2, r, 1, 1)
            self.grid.attach(self.text("masqué", False), 3, r, 1, 1)
            self.grid.attach(Gtk.Label(label="déjà en place" if hidden else "", xalign=0), 5, r, 1, 1)
            r += 1

    def picker(self, entry):
        pop = Gtk.Popover()
        sc = Gtk.ScrolledWindow(min_content_width=620, min_content_height=420)
        flow = Gtk.FlowBox(max_children_per_line=6, selection_mode=Gtk.SelectionMode.NONE,
                           row_spacing=6, column_spacing=6)
        for p in reserve_icons():
            b = Gtk.Button()
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            img = Gtk.Image.new_from_file(str(p))
            img.set_pixel_size(64)
            v.append(img)
            lab = Gtk.Label(label=p.stem.replace("dossier-", ""))
            lab.add_css_class("caption")
            v.append(lab)
            b.set_child(v)
            b.connect("clicked", lambda _b, s=p.stem: (pop.popdown(), self.set_icon(entry, s)))
            flow.append(b)
        sc.set_child(flow)
        pop.set_child(sc)
        return pop

    def set_icon(self, entry, stem):
        entry["icone"] = stem
        save_plan(self.plan)
        self.write(f"~/{entry['chemin']} : {stem or 'icône standard'} (pas encore appliqué)")
        GLib.idle_add(lambda: (self.reload(), False)[1])

    def remove_row(self, entry):
        self.plan["dossiers"].remove(entry)
        save_plan(self.plan)
        self.write(f"~/{entry['chemin']} retiré du plan")
        GLib.idle_add(lambda: (self.reload(), False)[1])

    def check_all(self, value):
        for _, _, c in self.rows:
            c.set_active(value)

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

    # ----- plan / réserve
    def on_add(self, *_):
        fd = Gtk.FileDialog(title="Dossier à ajouter au plan", initial_folder=Gio.File.new_for_path(str(HOME)))

        def done(dlg, res):
            try:
                p = Path(dlg.select_folder_finish(res).get_path())
            except GLib.Error:
                return
            try:
                chemin = str(p.relative_to(HOME))
            except ValueError:
                self.write("Seuls les dossiers de ton dossier personnel sont gérés.")
                return
            if any(e["chemin"] == chemin for e in self.plan["dossiers"]):
                self.write(f"~/{chemin} est déjà dans le plan.")
                return
            self.plan["dossiers"].append({"chemin": chemin, "icone": None,
                                          "creer": not chemin.startswith("Dropbox")})
            self.plan["dossiers"].sort(key=lambda e: e["chemin"].lower())
            save_plan(self.plan)
            self.write(f"~/{chemin} ajouté : choisis son icône avec « Choisir… »")
            self.reload()
        fd.select_folder(self, None, done)

    def on_import(self, *_):
        f = Gtk.FileFilter(name="Icônes SVG / PNG")
        f.add_pattern("*.svg")
        f.add_pattern("*.png")
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f)
        fd = Gtk.FileDialog(title="Icônes à importer", filters=store)

        def done(dlg, res):
            try:
                files = dlg.open_multiple_finish(res)
            except GLib.Error:
                return
            for i in range(files.get_n_items()):
                src = Path(files.get_item(i).get_path())
                stem = src.stem
                if not stem.startswith("dossier-"):
                    stem = "dossier-" + re.sub(r"^(folder|places?)-", "", stem)
                dst = RESERVE / f"{stem}{src.suffix}"
                shutil.copy2(src, dst)
                self.write(f"Importée : {src.name} → {dst.name}")
            self.reload()
        fd.open_multiple(self, None, done)

    # ----- actions
    def on_apply(self, *_):
        dossiers = [k for g, k, c in self.rows if g == "dossier" and c.get_active()]
        masques = [k for g, k, c in self.rows if g == "masque" and c.get_active()]
        if not dossiers and not masques:
            self.write("Rien de coché.")
            return
        detail = (f"{len(dossiers)} dossier(s) : création si besoin + icône.\n"
                  + (f"À masquer : {', '.join(masques)} (renommés en .Nom, user-dirs.dirs mis à jour).\n"
                     if masques else "")
                  + "\nL'état actuel est mis de côté avant : « Restaurer l'état d'avant » le remet.")
        self.confirm("Appliquer ?", detail, "Appliquer", lambda: self.do_apply(dossiers, masques))

    def do_apply(self, dossiers, masques):
        snap = snapshot(dossiers, masques)
        self.write(f"Instantané : {snap.name}")
        for name in masques:
            try:
                self.write(hide_folder(name))
            except OSError as e:
                self.write(f"{name} : {e}")
        plan = {e["chemin"]: e for e in self.plan["dossiers"]}
        for chemin in dossiers:
            e, p = plan[chemin], HOME / chemin
            if not p.exists():
                if not e.get("creer"):
                    self.write(f"~/{chemin} : absent, ignoré")
                    continue
                p.mkdir(parents=True)
                self.write(f"~/{chemin} : créé")
            target = icon_file(e.get("icone"))
            try:
                set_custom_icon(p, target.as_uri() if target else None)
                self.write(f"~/{chemin} : {target.name if target else 'icône standard'}")
            except GLib.Error as err:
                self.write(f"~/{chemin} : {err.message}")
        self.write("Fait. Si Fichiers était ouvert : Actions → Relancer Fichiers.")
        self.reload()

    def on_restore(self, *_):
        snaps = sorted(SNAPSHOTS.glob("*/instantane.json"), reverse=True) if SNAPSHOTS.is_dir() else []
        if not snaps:
            self.write("Aucun instantané : rien n'a encore été appliqué depuis cette fenêtre.")
            return
        dest = snaps[0].parent
        self.confirm("Restaurer l'état d'avant ?",
                     f"Instantané du {dest.name.replace('_', ' à ')} : icônes, dossiers masqués et "
                     "user-dirs.dirs reviennent comme avant le dernier « Appliquer ». Les dossiers "
                     "créés à ce moment-là sont retirés s'ils sont encore vides.",
                     "Restaurer", lambda: self.do_restore(dest))

    def do_restore(self, dest):
        for line in restore(dest):
            self.write(line)
        dest.rename(dest.with_name(dest.name + "-restaure"))
        self.reload()

    def on_export(self, *_):
        out = HOME / f"dossiers-ogu-{datetime.date.today()}.pyz"
        self.confirm("Exporter ?",
                     f"Crée {out.name} dans ton dossier personnel : cette appli avec ton plan actuel et "
                     f"ses {len(reserve_icons())} icônes (avec tes imports). C'est ce fichier-là qu'il faut garder.",
                     "Exporter", lambda: self.write(f"Exporté → {build_pyz(out)}"))

    def on_nautilus(self, *_):
        self.confirm("Relancer Fichiers ?",
                     "Ferme toutes les fenêtres de Fichiers pour qu'il relise les icônes. "
                     "Les copies en cours seraient interrompues.",
                     "Relancer", lambda: subprocess.Popen(["nautilus", "-q"]))


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.gitlab.shogu.DossiersOgu")

    def do_activate(self):
        sync_reserve()
        (self.get_active_window() or Window(self)).present()


if __name__ == "__main__":
    sys.exit(App().run(sys.argv))
