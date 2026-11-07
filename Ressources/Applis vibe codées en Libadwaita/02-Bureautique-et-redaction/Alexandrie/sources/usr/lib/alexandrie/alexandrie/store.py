"""Données persistantes : favoris à tags libres et panier d'extraits."""

import html as _html
import json
import time
from pathlib import Path

from gi.repository import GLib, GObject

from . import api

DATA_DIR = Path(GLib.get_user_data_dir()) / "alexandrie"


def _load(name, default):
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(name, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_DIR / (name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(DATA_DIR / name)


class Favorites(GObject.Object):
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        super().__init__()
        self.items = _load("favoris.json", [])

    def find(self, site, title):
        for f in self.items:
            if f["site"] == site and f["title"] == title:
                return f
        return None

    def set(self, site, title, tags):
        tags = sorted({t.strip() for t in tags if t.strip()}, key=str.casefold)
        f = self.find(site, title)
        if f:
            f["tags"] = tags
        else:
            self.items.append({"site": site, "title": title, "tags": tags, "added": int(time.time())})
        self._commit()

    def remove(self, site, title):
        self.items = [f for f in self.items if not (f["site"] == site and f["title"] == title)]
        self._commit()

    def all_tags(self):
        return sorted({t for f in self.items for t in f["tags"]}, key=str.casefold)

    def _commit(self):
        self.items.sort(key=lambda f: f["title"].casefold())
        _save("favoris.json", self.items)
        self.emit("changed")


def _norm(t):
    return " ".join((t or "").split()).casefold()


def item_key(it):
    """Clé de doublon ; None = jamais considéré comme doublon (blocs libres)."""
    k = it["kind"]
    if k == "text":
        return ("text", _norm(it.get("text")))
    if k == "image":
        return ("image", it.get("file") or it.get("src"))
    if k == "date":
        return ("date", it.get("date"), it.get("label"), it.get("source_title"))
    if k == "term":
        return ("term", _norm(it.get("word")), _norm(it.get("definition")))
    return None


class Basket(GObject.Object):
    """Éléments : {kind: text|image|date|term|block, …, source_title, url, license, site, added}."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        super().__init__()
        self.items = _load("panier.json", [])

    def contains(self, item):
        key = item_key(item)
        return key is not None and any(item_key(i) == key for i in self.items)

    def add(self, item):
        """Ajoute l'élément ; renvoie False s'il est déjà dans le panier."""
        if self.contains(item):
            return False
        item.setdefault("added", int(time.time()))
        self.items.append(item)
        self._commit()
        return True

    def update(self, idx, **fields):
        if 0 <= idx < len(self.items):
            self.items[idx].update(fields)
            self._commit()

    def remove(self, idx):
        if 0 <= idx < len(self.items):
            del self.items[idx]
            self._commit()

    def move(self, src, dst):
        if src == dst or not (0 <= src < len(self.items)) or not (0 <= dst < len(self.items)):
            return
        it = self.items.pop(src)
        self.items.insert(dst, it)
        self._commit()

    def clear(self):
        self.items = []
        self._commit()

    def _commit(self):
        _save("panier.json", self.items)
        self.emit("changed")


class History(GObject.Object):
    """Historique des articles ouverts (le plus récent en tête)."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}
    MAX = 150

    def __init__(self):
        super().__init__()
        self.items = _load("historique.json", [])

    def add(self, site, title, description=""):
        self.items = [h for h in self.items if not (h["site"] == site and h["title"] == title)]
        self.items.insert(0, {"site": site, "title": title, "description": description,
                              "ts": int(time.time())})
        del self.items[self.MAX:]
        self._commit()

    def remove(self, site, title):
        self.items = [h for h in self.items if not (h["site"] == site and h["title"] == title)]
        self._commit()

    def clear(self):
        self.items = []
        self._commit()

    def matching(self, text, site=None, limit=8):
        t = _norm(text)
        out = [h for h in self.items if (site is None or h["site"] == site) and t in _norm(h["title"])]
        return out[:limit]

    def _commit(self):
        _save("historique.json", self.items)
        self.emit("changed")


GENERIC = {lab for _pid, lab in api.DATE_PROPS}
BLOCK_LABELS = {"heading": "Titre", "instruction": "Consigne", "note": "Note"}


def date_label(it):
    """« naissance » pour les libellés génériques ; « Œuvre : Le Capital » tel quel."""
    return it["label"].lower() if it["label"] in GENERIC else it["label"]


def item_label(it):
    k = it["kind"]
    if k == "text":
        t = " ".join(it.get("text", "").split())
        return t[:140] + ("…" if len(t) > 140 else "")
    if k == "image":
        return it.get("caption") or it.get("file") or "Image"
    if k == "term":
        d = it.get("definition", "")
        return f"{it['word']} : {d[:110]}{'…' if len(d) > 110 else ''}"
    if k == "block":
        t = " ".join(it.get("text", "").split())
        return t[:140] + ("…" if len(t) > 140 else "")
    return f"{it['date']} · {date_label(it)}"


def item_subtitle(it):
    k = it["kind"]
    if k == "block":
        return BLOCK_LABELS.get(it.get("style"), "Bloc")
    if k == "term":
        return f"Glossaire · {it.get('pos') or 'Wiktionnaire'}"
    return it.get("source_title", "")


def _site_label(it):
    if it.get("site") in api.SITE_LABELS:
        return api.SITE_LABELS[it["site"]]
    host = (it.get("url") or "").split("/")[2:3]
    if host and host[0] in api.HOST_TO_SITE:
        return api.SITE_LABELS[api.HOST_TO_SITE[host[0]]]
    if "commons.wikimedia.org" in (it.get("url") or ""):
        return "Wikimedia Commons"
    return ""


def _consulted(it):
    ts = it.get("added")
    return time.strftime("%d/%m/%Y", time.localtime(ts)) if ts else ""


def source_line(it):
    """« Source : « Karl Marx », Wikipédia, CC BY-SA 4.0, consulté le 18/10/2026 — https://… »"""
    bits = []
    if it["kind"] == "image" and it.get("author"):
        bits.append(it["author"])
    title = it.get("source_title", "")
    if title.startswith(("File:", "Fichier:")):
        title = title.split(":", 1)[1]
    if title:
        bits.append(f"« {title} »")
    if _site_label(it):
        bits.append(_site_label(it))
    bits.append(it.get("license") or api.LICENSE)
    if _consulted(it):
        bits.append(f"consulté le {_consulted(it)}")
    line = ", ".join(bits)
    return f"Source : {line}" + (f" — {it['url']}" if it.get("url") else "")


def render(items, add_source, title=None, numbered=False):
    """Renvoie (html, texte brut) d'une fiche.

    numbered : « Document 1, 2… » sur les extraits et les images, avec leur source juste dessous
    (si add_source) au lieu de la liste des sources en fin de fiche.
    Le glossaire est toujours regroupé en fin de fiche, par ordre alphabétique."""
    esc = _html.escape
    parts, plain = [], []
    credit_style = 'style="font-size:8pt;color:#77767b;margin-top:2pt"'
    if title:
        parts.append(f"<h1>{esc(title)}</h1>")
        plain.append(title)
    n = 0
    terms = []
    for it in items:
        k = it["kind"]
        if k in ("text", "image") and numbered:
            n += 1
            head = f"Document {n}"
            lead = it.get("source_title", "") if k == "text" else (it.get("caption") or "")
            if k == "image":
                lead = lead.split(".")[0][:120]
            parts.append(f"<p><b>{head}</b>{' – ' + esc(lead) if lead else ''}</p>")
            plain.append(head + (f" – {lead}" if lead else ""))
        if k == "text":
            parts.append(it["html"])
            plain.append(it["text"])
        elif k == "image":
            cap = it.get("caption") or ""
            fig = f'<figure><img src="{esc(api.https(it["src"]))}" alt="{esc(cap)}">'
            if cap and not numbered:
                fig += f"<figcaption>{esc(cap)}</figcaption>"
            parts.append(fig + "</figure>")
            plain.append(f"[Image : {cap or it.get('file', '')}]")
        elif k == "date":
            parts.append(f"<p><b>{esc(it['date'])}</b> — {esc(it['source_title'])} "
                         f"({esc(date_label(it))})</p>")
            plain.append(f"{it['date']} — {it['source_title']} ({date_label(it)})")
        elif k == "term":
            terms.append(it)
        elif k == "block":
            paras = [p.strip() for p in it.get("text", "").split("\n") if p.strip()]
            style = it.get("style")
            if style == "heading":
                parts.append(f"<h2>{esc(' '.join(paras))}</h2>")
            elif style == "instruction":
                parts.extend(f"<p><b>{esc(p)}</b></p>" for p in paras)
            else:
                parts.extend(f"<p><i>{esc(p)}</i></p>" for p in paras)
            plain.append("\n".join(paras))
        if numbered and add_source and k in ("text", "image"):
            parts.append(f"<p class=\"credit\" {credit_style}>{esc(source_line(it))}</p>")
            plain.append(source_line(it))
    if terms:
        terms.sort(key=lambda t: t["word"].casefold())
        parts.append("<h2>Vocabulaire</h2>")
        plain.append("Vocabulaire")
        for t in terms:
            pos = f" <i>({esc(t['pos'])})</i>" if t.get("pos") else ""
            parts.append(f"<p><b>{esc(t['word'])}</b>{pos} : {esc(t['definition'])}</p>")
            plain.append(f"{t['word']}{' (' + t['pos'] + ')' if t.get('pos') else ''} : {t['definition']}")
    if add_source and not numbered:
        seen, srcs = set(), []
        for it in items:
            key = it.get("url")
            if key and key not in seen and it["kind"] not in ("block", "term"):
                seen.add(key)
                lic = it.get("license") or api.LICENSE
                who = f", {it['author']}" if it.get("author") else ""
                srcs.append((it.get("source_title", ""), key, f"{lic}{who}"))
        if srcs:
            line = " ; ".join(f"{t} — {u} ({lic})" for t, u, lic in srcs)
            parts.append(f'<p class="credit" {credit_style}>Sources : {esc(line)}</p>')
            plain.append(f"Sources : {line}")
    if terms and add_source:
        parts.append(f'<p class="credit" {credit_style}>Définitions : Wiktionnaire, CC BY-SA 4.0</p>')
        plain.append("Définitions : Wiktionnaire, CC BY-SA 4.0")
    return "\n".join(parts), "\n\n".join(p for p in plain if p)
