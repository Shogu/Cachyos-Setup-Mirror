"""Page Santé : une carte par source, avec un voyant."""
import datetime

from gi.repository import Adw, Gtk

from . import sources as s
from . import widgets as w

STATE_FR = {"running": "en marche", "degraded": "dégradé", "starting": "démarrage en cours",
            "initializing": "initialisation", "maintenance": "maintenance", "stopping": "arrêt en cours",
            "offline": "hors ligne"}


class HealthPage(Adw.Bin):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page = Adw.PreferencesPage()
        self.set_child(self.page)
        self.groups = []

    # ------------------------------------------------------------------ helpers
    def add(self, group):
        self.page.add(group)
        self.groups.append(group)
        return group

    def group(self, title, description=None):
        g = Adw.PreferencesGroup(title=title)
        if description:
            g.set_description(description)
        return self.add(g)

    def data(self, key):
        return self.window.data.get(key)

    def pending(self, *keys):
        return any(k in self.window.loading for k in keys) or any(self.data(k) is None for k in keys)

    # ------------------------------------------------------------------ rendu
    def refresh(self):
        w.clear_page(self.page, self.groups)
        hero = self.add(Adw.PreferencesGroup())
        verdicts = []
        verdicts += self.services()
        verdicts += self.boot()
        verdicts += self.kernel()
        verdicts += self.crashes()
        verdicts += self.space()
        verdicts += self.hardware()
        self.fill_hero(hero, verdicts)

    def fill_hero(self, group, verdicts):
        kinds = [k for k, _ in verdicts]
        worst = w.worst(kinds)
        notes = [text for kind, text in verdicts if kind == worst and text and worst != "ok"]
        box = Gtk.Box(spacing=18, margin_top=6, margin_bottom=12)
        if self.window.loading:
            icon = w.spinner(48)
            title, subtitle = "Auscultation en cours…", "Lecture des journaux et de l’état du système"
        else:
            icon = w.status_icon(worst, 56)
            icon.add_css_class("hero-icon")
            title = {"ok": "Rien à signaler", "warn": "Quelques points à surveiller",
                     "error": "Des problèmes demandent votre attention"}.get(worst, "Rien à signaler")
            subtitle = " · ".join(notes[:4]) or "Aucune secousse notable dans les sources consultées"
        box.append(icon)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        t = Gtk.Label(label=title, xalign=0, wrap=True)
        t.add_css_class("hero-title")
        sub = Gtk.Label(label=subtitle, xalign=0, wrap=True)
        sub.add_css_class("dim-label")
        text.append(t)
        text.append(sub)
        text.append(Gtk.Label(label=s.os_identity(), xalign=0, css_classes=["caption", "dim-label"]))
        box.append(text)
        group.add(box)

    # ------------------------------------------------------------------ services
    def services(self):
        g = self.group("Services")
        out = []
        state = self.data("state")
        if state and state.ok:
            value = state.value
            kind = "ok" if value == "running" else "error" if value == "degraded" else "info"
            g.add(w.row("État de systemd", STATE_FR.get(value, value), kind))
            if value == "degraded":
                out.append(("error", "systemd dégradé"))
        for key, title, user in (("failed", "Services système en échec", False),
                                 ("failed_user", "Services de session en échec", True)):
            res = self.data(key)
            if res is None:
                g.add(w.row(title, "Lecture…", "wait"))
                continue
            if res.status != "ok":
                g.add(w.row(title, res.detail or res.status, "off"))
                continue
            if not res.value:
                g.add(w.row(title, "Aucun", "ok"))
                out.append(("ok", ""))
                continue
            exp = w.expander(title, ", ".join(u["unit"] for u in res.value), "error")
            for unit in res.value:
                r = w.row(unit["unit"], f"{unit['sub']} · {unit['description']}", activatable=True)
                r.connect("activated", lambda _r, u=unit["unit"], usr=user:
                          self.window.show_unit(u.removesuffix(".service"), "user" if usr else "all"))
                exp.add_row(r)
            exp.set_expanded(True)
            g.add(exp)
            out.append(("error", f"{len(res.value)} service{'s' if len(res.value) > 1 else ''} en échec"))
        return out

    # ------------------------------------------------------------------ démarrage
    def boot(self):
        g = self.group("Démarrage")
        out = []
        for key, title, boot in (("errors", "Erreurs du démarrage actuel", "0"),
                                 ("errors_prev", "Erreurs du démarrage précédent", "-1")):
            res = self.data(key)
            if res is None:
                g.add(w.row(title, "Lecture du journal…", "wait"))
                continue
            if res.status not in ("ok", "empty"):
                g.add(w.row(title, res.detail or res.status, "off"))
                continue
            events = res.value or []
            groups = s.group(events)
            crit = sum(1 for e in events if e.priority <= 2)
            if not events:
                sub, kind = ("Aucune" if res.status == "ok" or not res.detail else res.detail), "ok"
            else:
                sub = (f"{len(events)} message{'s' if len(events) > 1 else ''} en "
                       f"{len(groups)} groupe{'s' if len(groups) > 1 else ''}")
                if crit:
                    sub += f" · dont {crit} critiques ou pires"
                top = groups[0][0]
                sub += f"\nPlus grave : {top.unit} — {top.message.splitlines()[0][:90]}"
                kind = "error" if crit else "warn"
            if res.detail == "partial":
                sub += "\nJournal partiel : ajoutez-vous au groupe wheel ou systemd-journal"
            r = w.row(title, sub, kind, activatable=bool(events))
            if events:
                r.connect("activated", lambda *_r, b=boot, t=title: self.window.open_errors(b, t))
                if boot == "0":
                    out.append((kind, f"{len(groups)} groupe{'s' if len(groups) > 1 else ''} d’erreurs au démarrage"))
            g.add(r)

        sd = self.data("shutdown")
        if sd is None:
            g.add(w.row("Fin du démarrage précédent", "Lecture…", "wait"))
        elif sd.ok:
            last = sd.value["last"]
            if sd.value["clean"]:
                g.add(w.row("Fin du démarrage précédent", f"Arrêt propre · {last.clock(True)}", "ok"))
            else:
                r = w.row("Fin du démarrage précédent",
                          f"Arrêt brutal probable (plantage, gel, coupure de courant) · dernier message "
                          f"à {last.clock(True)} : {last.unit} — {last.message.splitlines()[0][:80]}",
                          "warn", activatable=True)
                r.connect("activated", lambda *_r, e=last: self.window.open_event(e, 1, "-1"))
                g.add(r)
                out.append(("warn", "arrêt brutal au démarrage précédent"))
        elif sd.status != "empty":
            g.add(w.row("Fin du démarrage précédent", sd.detail or sd.status, "off"))

        an = self.data("analyze")
        if an is None:
            g.add(w.row("Durée du démarrage", "Mesure…", "wait"))
        elif an.ok:
            total = an.value["total"]
            kind = "ok" if total < 30 else "warn"
            r = w.row("Durée du démarrage", an.value["target"] or "", kind,
                      value=s.human(total), activatable=True)
            r.connect("activated", lambda *_: self.window.stack.set_visible_child_name("boot"))
            g.add(r)
            if kind == "warn":
                out.append(("warn", f"démarrage lent ({s.human(total)})"))
        else:
            g.add(w.row("Durée du démarrage", an.detail or an.status, "off"))
        return out

    # ------------------------------------------------------------------ noyau
    def kernel(self):
        g = self.group("Noyau")
        out = []
        params = self.data("params")
        if params is None:
            g.add(w.row("Paramètres de la ligne de commande", "Lecture…", "wait"))
        else:
            cmdline, reports = params.value or ("", [])
            kind = "warn" if reports else ("ok" if params.ok else "off")
            sub = (f"{len(reports)} paramètre(s) inconnu(s) ou ignoré(s)" if reports
                   else "Aucun paramètre refusé par le noyau" if params.ok else params.detail)
            exp = w.expander("Paramètres de la ligne de commande", sub, kind)
            exp.add_row(self.mono_row(cmdline or "(ligne de commande illisible)"))
            for e in reports:
                exp.add_row(w.row(e.message, e.clock()))
            g.add(exp)
            if reports:
                out.append(("warn", "paramètres noyau ignorés"))
        tn = self.data("taint")
        if tn and tn.ok:
            flags = tn.value["flags"]
            serious = [f for f in flags if f[2]]
            kind = "error" if any(f[0] in "DMBL" for f in serious) else "warn" if serious else "ok"
            if not flags:
                g.add(w.row("Intégrité du noyau (taint)", "Aucune marque", "ok"))
            else:
                exp = w.expander("Intégrité du noyau (taint)",
                                 " ".join(f[0] for f in flags) + f"  (valeur {tn.value['value']})", kind)
                for flag, text, bad in flags:
                    exp.add_row(w.row(f"{flag} — {text}", "à examiner" if bad else "courant, sans gravité",
                                      "warn" if bad else "info"))
                g.add(exp)
            if serious:
                out.append((kind, "noyau marqué : " + "".join(f[0] for f in serious)))
        return out

    def mono_row(self, text):
        r = Adw.PreferencesRow(activatable=False)
        label = Gtk.Label(label=text, xalign=0, wrap=True, selectable=True,
                          margin_top=10, margin_bottom=10, margin_start=12, margin_end=12)
        label.add_css_class("monospace")
        r.set_child(label)
        return r

    # ------------------------------------------------------------------ plantages
    def crashes(self):
        g = self.group("Plantages d’applications", "coredumpctl, 30 derniers jours")
        res = self.data("coredumps")
        if res is None:
            g.add(w.row("Coredumps", "Lecture…", "wait"))
            return []
        if res.status == "disabled":
            g.add(w.row("Enregistrement désactivé", res.detail, "off"))
            return []
        if res.status == "empty":
            g.add(w.row("Aucun plantage enregistré", "", "ok"))
            return [("ok", "")]
        if res.status != "ok":
            g.add(w.row("Coredumps", res.detail or res.status, "off"))
            return []
        exp = w.expander(f"{len(res.value)} plantage(s)",
                         ", ".join(sorted({d['exe'].rsplit('/', 1)[-1] for d in res.value}))[:120], "warn")
        for d in res.value[:40]:
            when = datetime.datetime.fromtimestamp(d["time"] / 1e6).strftime("%d/%m %H:%M")
            exp.add_row(w.row(d["exe"].rsplit("/", 1)[-1],
                              f"{when} · {s.SIGNALS.get(d['sig'], d['sig'])} · PID {d['pid']} · {d['exe']}"))
        g.add(exp)
        return [("warn", f"{len(res.value)} plantage(s) en 30 jours")]

    # ------------------------------------------------------------------ espace
    def space(self):
        g = self.group("Espace disque")
        res = self.data("space")
        if res is None:
            g.add(w.row("Partitions", "Lecture…", "wait"))
            return []
        if not res.ok:
            g.add(w.row("Partitions", res.detail or "Aucune partition reconnue", "off"))
            return []
        out = []
        for part in res.value:
            ratio = part["used_ratio"]
            small = part["fstype"] == "vfat"
            if ratio > 0.95 or (small and part["free"] < 32 * 2**20):
                kind = "error"
            elif ratio > 0.85 or (small and part["free"] < 80 * 2**20):
                kind = "warn"
            else:
                kind = "ok"
            sub = f"{part['fstype']} · {part['source']}"
            if small:
                sub += " · partition de démarrage (noyaux et initramfs)"
            r = w.row(part["target"], sub, kind)
            bar = Gtk.LevelBar(min_value=0, max_value=1, value=ratio, valign=Gtk.Align.CENTER)
            bar.set_size_request(110, -1)
            bar.add_offset_value("low", 0.85)
            bar.add_offset_value("high", 0.95)
            bar.add_offset_value("full", 1)
            r.add_suffix(bar)
            r.add_suffix(w.value_label(f"{s.size(part['free'])} libres\nsur {s.size(part['total'])}"))
            g.add(r)
            if kind != "ok":
                out.append((kind, f"{part['target']} presque plein"))
        return out

    # ------------------------------------------------------------------ matériel
    def hardware(self):
        g = self.group("Matériel et systèmes de fichiers",
                       "SMART, compteurs d’erreurs btrfs, contrôle de la partition FAT")
        if "hardware" in self.window.loading:
            g.add(w.row("Vérification en cours…", "Lecture seule, rien n’est modifié", "wait"))
            return []
        res = self.data("hardware")
        if res is None:
            r = w.row("Vérification administrateur",
                      "Demande votre mot de passe une fois. Lecture seule, rien n’est modifié.", "off")
            r.add_suffix(w.button("Vérifier", css=("suggested-action",), callback=self.window.run_hardware))
            g.add(r)
            return []
        if not res.ok:
            r = w.row("Vérification administrateur", res.detail or res.status, "off")
            r.add_suffix(w.button("Réessayer", callback=self.window.run_hardware))
            g.add(r)
            return []
        out = []
        for title, kind, sub in hardware_summary(res.value):
            r = w.row(title, sub, kind, activatable=True)
            r.connect("activated", lambda *_: self.window.stack.set_visible_child_name("storage"))
            g.add(r)
            if kind in ("warn", "error"):
                out.append((kind, title))
        return out


def smart_verdict(disk):
    if disk.get("error"):
        return "off", disk["error"]
    notes = []
    kind = "ok"
    if disk.get("passed") is False:
        return "error", "Le disque signale un échec SMART"
    if disk.get("kind") == "nvme":
        if disk.get("critical_warning"):
            kind = "error"; notes.append(f"avertissement critique {disk['critical_warning']}")
        if disk.get("media_errors"):
            kind = "error"; notes.append(f"{disk['media_errors']} erreur(s) média")
        used = disk.get("percentage_used")
        if used is not None:
            if used >= 90:
                kind = "error" if used >= 100 else max(kind, "warn", key=w.RANK.get)
            notes.append(f"usure {used} %")
        spare, thr = disk.get("available_spare"), disk.get("available_spare_threshold")
        if spare is not None and thr is not None and spare <= thr:
            kind = "error"; notes.append(f"réserve {spare} %")
    else:
        for key, label in (("reallocated", "réalloués"), ("pending", "en attente"),
                           ("uncorrectable", "non corrigibles")):
            if disk.get(key):
                kind = "error" if key != "reallocated" else max(kind, "warn", key=w.RANK.get)
                notes.append(f"{disk[key]} secteurs {label}")
    temp = disk.get("temperature")
    if temp is not None:
        if temp >= 70:
            kind = max(kind, "warn", key=w.RANK.get)
        notes.append(f"{temp} °C")
    return kind, " · ".join(notes) or "Aucune anomalie"


def btrfs_total(fs):
    return sum(sum(v.values()) for v in fs.get("devices", {}).values())


def hardware_summary(value):
    rows = []
    sm = value.get("smart", {})
    if sm.get("status") == "missing":
        rows.append(("SMART", "off", sm.get("detail", "")))
    for disk in sm.get("disks", []):
        kind, sub = smart_verdict(disk)
        rows.append((f"SMART · {disk.get('model', disk['name'])}", kind, sub))
    bt = value.get("btrfs", {})
    if bt.get("status") == "missing":
        rows.append(("btrfs", "off", bt.get("detail", "")))
    for fs in bt.get("filesystems", []):
        total = btrfs_total(fs)
        rows.append((f"btrfs · {fs['target']}", "error" if total else "ok",
                     f"{total} erreur(s) cumulée(s)" if total else "Aucune erreur enregistrée"))
    fat = value.get("fat", {})
    if fat.get("status") == "missing":
        rows.append(("Partition FAT", "off", fat.get("detail", "")))
    for part in fat.get("partitions", []):
        kind = "warn" if part["issues"] else "ok"
        rows.append((f"FAT · {part['target']}", kind,
                     f"{len(part['issues'])} remarque(s) de fsck.fat" if part["issues"] else "Système de fichiers sain"))
    return rows
