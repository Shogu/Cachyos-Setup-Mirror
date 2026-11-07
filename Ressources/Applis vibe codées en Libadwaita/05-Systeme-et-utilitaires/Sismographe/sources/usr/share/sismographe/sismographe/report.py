"""Textes à copier-coller : une erreur seule, ou le rapport complet."""
import datetime

from . import sources as s


def boot_label(boot):
    boot = str(boot)
    if boot in ("0", ""):
        return "démarrage actuel"
    if boot == "-1":
        return "démarrage précédent"
    return f"démarrage {boot}"


def event_block(event, count=1, boot="0", context=()):
    """Bloc Markdown prêt à coller dans un forum, un ticket ou une discussion."""
    where = "journal pacman" if event.source == "pacman" else boot_label(boot)
    lines = [f"**{s.LEVELS[event.priority]} relevée par Sismographe**", "",
             f"- Unité : `{event.unit}`" + (f" (PID {event.pid})" if event.pid else ""),
             f"- Niveau : {s.LEVELS[event.priority]} (priorité {event.priority})",
             f"- Date : {event.full_date} · {where}",
             f"- Système : {s.os_identity()}"]
    if count > 1:
        lines.append(f"- Occurrences : {count} messages semblables")
    lines += ["", "```", event.message.strip(), "```"]
    others = [e for e in context if e != event]
    if others:
        lines += ["", "Contexte (même unité, une minute avant et après) :", "```"]
        for other in context:
            mark = "→" if other == event else " "
            lines.append(f"{mark} {other.clock()} {s.SHORT_LEVELS[other.priority]} "
                         f"{other.message.strip().replace(chr(10), ' ⏎ ')[:300]}")
        lines.append("```")
    if event.source != "pacman":
        command = "journalctl -k" if event.unit == "kernel" else (
            f"journalctl --user -u {event.unit}" if event.source == "user" else f"journalctl -u {event.unit}")
        lines += ["", f"Pour revoir : `{command} -b {boot}`"]
    return "\n".join(lines) + "\n"


def full_report(data):
    """data : dictionnaire rempli par la fenêtre (résultats des collecteurs)."""
    out = ["SISMOGRAPHE — ÉTAT DU SYSTÈME",
           "=" * 52,
           f"Généré le {datetime.datetime.now().astimezone():%Y-%m-%d %H:%M:%S %Z}",
           s.os_identity(), ""]

    state = data.get("state")
    if state and state.ok:
        out.append(f"État systemd : {state.value}")

    for title, key in (("Services système en échec", "failed"), ("Services utilisateur en échec", "failed_user")):
        res = data.get(key)
        out += ["", title.upper(), "-" * 52]
        if not res or res.status != "ok":
            out.append(res.detail if res else "non chargé")
        elif not res.value:
            out.append("Aucun")
        else:
            out += [f"  {u['unit']} ({u['sub']}) — {u['description']}" for u in res.value]

    out += ["", "DÉMARRAGE", "-" * 52]
    an = data.get("analyze")
    if an and an.ok:
        out.append("  " + " + ".join(f"{s.human(v)} ({k})" for k, v in an.value["stages"])
                   + f" = {s.human(an.value['total'])}")
        if an.value["target"]:
            out.append("  " + an.value["target"])
    elif an:
        out.append("  " + (an.detail or an.status))
    bl = data.get("blame")
    if bl and bl.ok:
        out.append("  Unités les plus lentes :")
        out += [f"    {s.human(sec):>12}  {unit}" for unit, sec in bl.value[:10]]

    out += ["", "ERREURS DU DÉMARRAGE ACTUEL (priorité 0–3)", "-" * 52]
    errs = data.get("errors")
    if errs and errs.status in ("ok", "empty"):
        groups = s.group(errs.value or [])
        out.append(f"{len(errs.value or [])} messages en {len(groups)} groupes")
        for event, count in groups[:60]:
            out.append(f"[{s.LEVELS[event.priority]}] {event.unit} · {event.clock()} · ×{count}")
            out.append("    " + event.message.strip().replace("\n", " ⏎ ")[:400])
    elif errs:
        out.append(errs.detail or errs.status)

    prev = data.get("errors_prev")
    if prev and prev.status in ("ok", "empty"):
        out.append(f"\nDémarrage précédent : {len(prev.value or [])} messages de priorité 0–3")
    sd = data.get("shutdown")
    if sd and sd.ok:
        last = sd.value["last"]
        out.append("Fin du démarrage précédent : " + ("arrêt propre" if sd.value["clean"] else
                   f"ARRÊT BRUTAL probable — dernier message {last.full_date} {last.unit} : "
                   f"{last.message.strip()[:200]}"))

    out += ["", "NOYAU", "-" * 52]
    params = data.get("params")
    if params and params.value:
        cmdline, reports = params.value
        out.append("Ligne de commande : " + cmdline)
        out += ["Paramètre signalé : " + e.message for e in reports] or ["Aucun paramètre inconnu signalé"]
    tn = data.get("taint")
    if tn and tn.ok:
        out.append("Taint : " + (", ".join(f"{f} {d}" for f, d, _ in tn.value["flags"]) or "aucun"))

    out += ["", "PLANTAGES (coredumps, 30 jours)", "-" * 52]
    cd = data.get("coredumps")
    if cd and cd.status == "ok":
        for d in cd.value[:30]:
            when = datetime.datetime.fromtimestamp(d["time"] / 1e6).strftime("%Y-%m-%d %H:%M")
            out.append(f"  {when}  {d['exe']}  {s.SIGNALS.get(d['sig'], d['sig'])}")
    elif cd:
        out.append("  " + (cd.detail or ("Aucun" if cd.status == "empty" else cd.status)))

    sp = data.get("space")
    if sp and sp.ok:
        out += ["", "ESPACE", "-" * 52]
        out += [f"  {r['target']:<10} {r['fstype']:<6} {s.size(r['free'])} libres / {s.size(r['total'])}"
                for r in sp.value]

    hw = data.get("hardware")
    if hw and hw.ok:
        out += ["", "MATÉRIEL (vérification administrateur)", "-" * 52]
        for disk in hw.value.get("smart", {}).get("disks", []):
            verdict = {True: "OK", False: "ÉCHEC", None: "?"}[disk.get("passed")]
            extra = (f", usure {disk.get('percentage_used')} %, erreurs média {disk.get('media_errors')}"
                     if disk.get("kind") == "nvme" else
                     f", réalloués {disk.get('reallocated')}, en attente {disk.get('pending')}")
            out.append(f"  SMART {disk['name']} ({disk.get('model')}) : {verdict}{extra}")
        for fs in hw.value.get("btrfs", {}).get("filesystems", []):
            total = sum(sum(v.values()) for v in fs["devices"].values())
            out.append(f"  btrfs {fs['target']} : {total} erreur(s) cumulée(s)")
        for part in hw.value.get("fat", {}).get("partitions", []):
            out.append(f"  FAT {part['target']} ({part['source']}) : "
                       + ("aucun problème" if not part["issues"] else f"{len(part['issues'])} remarque(s)"))
            out += ["      " + l for l in part["issues"]]
    return "\n".join(out).rstrip() + "\n"
