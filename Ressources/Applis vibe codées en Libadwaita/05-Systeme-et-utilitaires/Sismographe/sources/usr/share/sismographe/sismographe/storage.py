"""Page Stockage : SMART, btrfs device stats, contrôle FAT (via l’assistant root)."""
from gi.repository import Adw, Gtk

from . import sources as s
from . import widgets as w
from .health import btrfs_total, smart_verdict

BTRFS_FR = {"write_io_errs": "écriture", "read_io_errs": "lecture", "flush_io_errs": "purge",
            "corruption_errs": "corruption", "generation_errs": "génération"}


class StoragePage(Adw.Bin):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.groups = []
        self.page = Adw.PreferencesPage()
        self.intro = Adw.StatusPage(icon_name="drive-harddisk-symbolic", title="Santé du stockage",
                                    description="SMART des disques, compteurs d’erreurs btrfs et contrôle "
                                                "de la partition de démarrage FAT.\nCes lectures demandent les "
                                                "droits administrateur. Rien n’est modifié.")
        self.intro.set_child(w.button("Lancer la vérification", css=("suggested-action", "pill"),
                                      callback=self.window.run_hardware))
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(self.intro, "intro")
        self.stack.add_named(w.loading_page("Vérification en cours…"), "loading")
        self.stack.add_named(self.page, "result")
        self.set_child(self.stack)

    def add(self, title, description=None):
        g = Adw.PreferencesGroup(title=title)
        if description:
            g.set_description(description)
        self.page.add(g)
        self.groups.append(g)
        return g

    def refresh(self):
        if "hardware" in self.window.loading:
            self.stack.set_visible_child_name("loading")
            return
        res = self.window.data.get("hardware")
        if res is None:
            self.stack.set_visible_child_name("intro")
            return
        if not res.ok:
            self.intro.set_description(res.detail or res.status)
            self.stack.set_visible_child_name("intro")
            return
        w.clear_page(self.page, self.groups)
        self.smart(res.value.get("smart", {}))
        self.btrfs(res.value.get("btrfs", {}))
        self.fat(res.value.get("fat", {}))
        again = self.add("")
        again.add(w.button("Relancer la vérification", "view-refresh-symbolic", css=("pill",),
                           callback=self.window.run_hardware))
        self.stack.set_visible_child_name("result")

    # ------------------------------------------------------------------ SMART
    def smart(self, data):
        if data.get("status") == "missing":
            self.add("SMART").add(w.row("smartctl absent", data.get("detail", ""), "off"))
            return
        if not data.get("disks"):
            self.add("SMART").add(w.row("Aucun disque compatible détecté", status="off"))
            return
        for disk in data["disks"]:
            cap = s.size(disk["capacity"]) if disk.get("capacity") else ""
            g = self.add(disk.get("model", "Disque"), " · ".join(x for x in (disk["name"], cap) if x))
            kind, sub = smart_verdict(disk)
            verdict = {True: "Réussi", False: "ÉCHEC", None: "Inconnu"}[disk.get("passed")]
            g.add(w.row("Bilan SMART", sub, kind, value=verdict))
            if disk.get("error"):
                continue
            if disk.get("kind") == "nvme":
                used = disk.get("percentage_used")
                if used is not None:
                    r = w.row("Usure estimée", "Pourcentage de l’endurance prévue par le fabricant",
                              "error" if used >= 100 else "warn" if used >= 80 else None)
                    bar = Gtk.LevelBar(min_value=0, max_value=100, value=min(used, 100), valign=Gtk.Align.CENTER)
                    bar.set_size_request(110, -1)
                    bar.add_offset_value("low", 80)
                    bar.add_offset_value("high", 95)
                    r.add_suffix(bar)
                    r.add_suffix(w.value_label(f"{used} %"))
                    g.add(r)
                self.num(g, "Réserve disponible", disk.get("available_spare"), " %",
                         sub=f"seuil d’alerte : {disk.get('available_spare_threshold')} %",
                         bad=lambda v: v <= (disk.get("available_spare_threshold") or 0))
                self.num(g, "Erreurs média et intégrité", disk.get("media_errors"), bad=lambda v: v > 0)
                self.num(g, "Avertissement critique", disk.get("critical_warning"), bad=lambda v: v > 0,
                         fmt=lambda v: "aucun" if not v else f"code {v}")
                self.num(g, "Entrées du journal d’erreurs", disk.get("error_log_entries"),
                         sub="souvent des commandes refusées sans gravité")
                self.num(g, "Arrêts brutaux", disk.get("unsafe_shutdowns"),
                         sub="coupures sans arrêt propre du disque")
                if disk.get("data_written_tb") is not None:
                    g.add(w.row("Données écrites", value=f"{disk['data_written_tb']:.2f} To".replace(".", ",")))
            else:
                self.num(g, "Secteurs réalloués", disk.get("reallocated"), bad=lambda v: v > 0)
                self.num(g, "Secteurs en attente", disk.get("pending"), bad=lambda v: v > 0)
                self.num(g, "Secteurs non corrigibles", disk.get("uncorrectable"), bad=lambda v: v > 0)
                self.num(g, "Erreurs CRC (câble)", disk.get("crc_errors"), bad=lambda v: v > 0)
            self.num(g, "Température", disk.get("temperature"), " °C", bad=lambda v: v >= 70)
            self.num(g, "Heures de fonctionnement", disk.get("power_on_hours"), " h")

    @staticmethod
    def num(group, title, value, unit="", sub="", bad=None, fmt=None):
        if value is None:
            return
        kind = "error" if bad and bad(value) else None
        text = fmt(value) if fmt else f"{value}{unit}"
        group.add(w.row(title, sub, kind, value=text))

    # ------------------------------------------------------------------ btrfs
    def btrfs(self, data):
        if data.get("status") == "missing":
            self.add("btrfs").add(w.row("btrfs-progs absent", data.get("detail", ""), "off"))
            return
        for fs in data.get("filesystems", []):
            total = btrfs_total(fs)
            g = self.add(f"btrfs · {fs['target']}", f"UUID {fs['uuid']}")
            if fs.get("error"):
                g.add(w.row("Lecture impossible", fs["error"], "off"))
                continue
            for dev, counters in fs["devices"].items():
                errs = sum(counters.values())
                detail = " · ".join(f"{BTRFS_FR.get(k, k)} {v}" for k, v in counters.items())
                g.add(w.row(dev, detail, "error" if errs else "ok",
                            value="aucune erreur" if not errs else f"{errs} erreur(s)"))
            if total:
                g.add(w.row("Que faire ?",
                            "Lancez « btrfs scrub start » sur ce volume, vérifiez SMART, puis remettez les "
                            "compteurs à zéro avec « btrfs device stats -z » une fois la cause traitée.",
                            "info", wrap_subtitle=True))

    # ------------------------------------------------------------------ FAT
    def fat(self, data):
        if data.get("status") == "missing":
            self.add("Partition FAT").add(w.row("dosfstools absent", data.get("detail", ""), "off"))
            return
        if not data.get("partitions"):
            self.add("Partition FAT").add(w.row("Aucune partition FAT montée", status="off"))
            return
        for part in data["partitions"]:
            g = self.add(f"Partition FAT · {part['target']}", f"{part['source']} · fsck.fat -n (lecture seule)")
            g.add(w.row("Contrôle", part.get("summary", ""), "warn" if part["issues"] else "ok",
                        value="remarques" if part["issues"] else "sain"))
            if part.get("dirty_while_mounted"):
                g.add(w.row("Bit « sale » ignoré", "Linux le pose sur toute partition FAT montée : "
                                                    "ce n’est pas une erreur.", "info", wrap_subtitle=True))
            if part["issues"]:
                g.add(w.mono_block("\n".join(part["issues"]), wrap=True))
            sp = self.window.data.get("space")
            if sp and sp.ok:
                for row in sp.value:
                    if row["target"] == part["target"]:
                        g.add(w.row("Espace libre", value=f"{s.size(row['free'])} sur {s.size(row['total'])}"))
