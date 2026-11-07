"""Accès aux API Wikimedia (Wikipédia, Wikisource, Wiktionnaire, Wikidata, Commons)."""

import html as _html
import re
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
from gi.repository import GLib

APP_ID = "io.gitlab.shogu.Alexandrie"
VERSION = "1.3.2"
UA = f"Alexandrie/{VERSION} ({APP_ID}; visionneuse GNOME personnelle)"

SITES = {"wikipedia": "fr.wikipedia.org", "vikidia": "fr.vikidia.org", "wikisource": "fr.wikisource.org"}
HOST_TO_SITE = {v: k for k, v in SITES.items()}
SITE_LABELS = {"wikipedia": "Wikipédia", "vikidia": "Vikidia", "wikisource": "Wikisource"}
# Vikidia n'est pas un projet Wikimedia : pas de REST Parsoid garanti, on passe par l'API Action.
LEGACY = {"vikidia"}
LICENSE = "CC BY-SA 4.0"

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Api-User-Agent": UA})
_pool = ThreadPoolExecutor(max_workers=10)


class NotFound(Exception):
    pass


def run_async(func, callback, *args):
    """Exécute func(*args) dans un fil et rappelle callback(résultat, erreur) dans la boucle GTK."""

    def worker():
        try:
            res, err = func(*args), None
        except Exception as e:  # noqa: BLE001
            res, err = None, e
        GLib.idle_add(lambda: callback(res, err) and False)

    threading.Thread(target=worker, daemon=True).start()


def pool_async(func, callback, *args):
    """Comme run_async, mais via un petit pool (vignettes)."""

    def worker():
        try:
            res, err = func(*args), None
        except Exception as e:  # noqa: BLE001
            res, err = None, e
        GLib.idle_add(lambda: callback(res, err) and False)

    _pool.submit(worker)


def session():
    return _session


def quote_title(title):
    return urllib.parse.quote(title.replace(" ", "_"), safe="")


def page_url(site, title):
    return f"https://{SITES[site]}/wiki/{quote_title(title)}"


def https(url):
    if url and url.startswith("//"):
        return "https:" + url
    return url


def strip_tags(s):
    return _html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _body(html_text):
    m = re.search(r"<body[^>]*>(.*)</body>", html_text, re.S)
    return m.group(1) if m else html_text


# --- Recherche -------------------------------------------------------------

def _api(site, **params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", 2)
    r = _session.get(f"https://{SITES[site]}/w/api.php", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def search_titles(site, query, limit=8):
    if site in LEGACY:
        d = _api(site, action="query", list="prefixsearch", pssearch=query, pslimit=limit)
        return [{"title": p["title"], "description": "", "thumb": None}
                for p in d.get("query", {}).get("prefixsearch", [])]
    r = _session.get(f"https://{SITES[site]}/w/rest.php/v1/search/title",
                     params={"q": query, "limit": limit}, timeout=10)
    r.raise_for_status()
    out = []
    for p in r.json().get("pages", []):
        out.append({
            "title": p.get("title", ""),
            "description": p.get("description") or "",
            "thumb": https((p.get("thumbnail") or {}).get("url")),
        })
    return out


def search_fulltext(site, query, limit=1):
    if site in LEGACY:
        d = _api(site, action="query", list="search", srsearch=query, srlimit=limit)
        return [p["title"] for p in d.get("query", {}).get("search", [])]
    r = _session.get(f"https://{SITES[site]}/w/rest.php/v1/search/page",
                     params={"q": query, "limit": limit}, timeout=10)
    r.raise_for_status()
    return [p["title"] for p in r.json().get("pages", [])]


# --- Articles --------------------------------------------------------------

def _canonical_title(html_text, fallback):
    """Titre canonique lu dans l'en-tête Parsoid (indépendant de l'URL finale)."""
    m = re.search(r'<link[^>]+rel="dc:isVersionOf"[^>]+href="[^"]*/wiki/([^"?#]+)"', html_text)
    if not m:
        m = re.search(r'href="[^"]*/wiki/([^"?#]+)"[^>]+rel="dc:isVersionOf"', html_text)
    if m:
        return urllib.parse.unquote(m.group(1)).replace("_", " ")
    m = re.search(r"<title>(.*?)</title>", html_text, re.S)
    if m and m.group(1).strip():
        return strip_tags(m.group(1))
    return fallback


def fetch_page_legacy(site, title):
    """HTML classique (action=parse), pour les wikis sans Parsoid public."""
    d = _api(site, action="parse", page=title, prop="text|displaytitle", redirects=1,
             disableeditsection=1, disabletoc=1)
    if "error" in d:
        if d["error"].get("code") == "missingtitle":
            raise NotFound(title)
        raise RuntimeError(d["error"].get("info", "erreur"))
    p = d["parse"]
    return p.get("title", title), p.get("text", "")


def fetch_page(site, title):
    if site in LEGACY:
        return fetch_page_legacy(site, title)
    """HTML Parsoid d'une page. L'ancienne API rest_v1 redirige parfois vers rest.php :
    le titre est donc toujours relu dans le HTML, jamais déduit de l'URL."""
    r = _session.get(f"https://{SITES[site]}/api/rest_v1/page/html/{quote_title(title)}",
                     params={"redirect": "true"}, timeout=25)
    if r.status_code == 404:
        raise NotFound(title)
    if not r.ok:
        r = _session.get(f"https://{SITES[site]}/w/rest.php/v1/page/{quote_title(title)}/html", timeout=25)
        if r.status_code == 404:
            raise NotFound(title)
        r.raise_for_status()
    return _canonical_title(r.text, title), _body(r.text)


def fetch_summary(site, title):
    """Résumé via l'API Action (stable) : extrait, vignette, description, Wikidata, coordonnées."""
    params = {"action": "query", "format": "json", "formatversion": 2, "redirects": 1, "titles": title,
              "prop": "extracts|pageimages|pageprops|description|coordinates",
              "exintro": 1, "explaintext": 1, "exsentences": 4, "pithumbsize": 240,
              "ppprop": "wikibase_item"}
    if site != "wikipedia":
        params["prop"] = "extracts|pageimages|pageprops"
        params.pop("ppprop")
    r = _session.get(f"https://{SITES[site]}/w/api.php", params=params, timeout=10)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing") or pages[0].get("invalid"):
        return None
    p = pages[0]
    coords = None
    if p.get("coordinates"):
        c = p["coordinates"][0]
        coords = {"lat": c["lat"], "lon": c["lon"]}
    return {
        "title": p.get("title", title),
        "description": p.get("description") or "",
        "extract": p.get("extract") or "",
        "thumb": (p.get("thumbnail") or {}).get("source"),
        "qid": (p.get("pageprops") or {}).get("wikibase_item"),
        "coords": coords,
    }


def load_article(site, title):
    """Article + résumé (description, élément Wikidata, coordonnées)."""
    try:
        final, body = fetch_page(site, title)
    except NotFound:
        # Pas de page exacte : on tente la recherche plein texte.
        hits = search_fulltext(site, title)
        if not hits:
            raise
        final, body = fetch_page(site, hits[0])
    try:
        summary = fetch_summary(site, final) or {}
    except Exception:  # noqa: BLE001
        summary = {}
    if site == "vikidia" and not summary.get("qid"):
        # Vikidia n'a pas d'élément Wikidata : on emprunte celui de l'article Wikipédia homonyme.
        try:
            wp = fetch_summary("wikipedia", final) or {}
            for k in ("qid", "coords", "description"):
                if wp.get(k) and not summary.get(k):
                    summary[k] = wp[k]
        except Exception:  # noqa: BLE001
            pass
    return {"site": site, "title": final, "body": body, "summary": summary}


def related(site, title, limit=6):
    """Articles proches (CirrusSearch « morelike: »), Wikipédia seulement."""
    if site != "wikipedia":
        return []
    d = _api(site, action="query", list="search", srsearch=f"morelike:{title}", srlimit=limit,
             srnamespace=0, srprop="")
    return [p["title"] for p in d.get("query", {}).get("search", []) if p["title"] != title]


# --- Wikidata : dates clés -------------------------------------------------

DATE_PROPS = [
    ("P569", "Naissance"), ("P570", "Décès"), ("P571", "Fondation"), ("P576", "Dissolution"),
    ("P580", "Début"), ("P582", "Fin"), ("P585", "Date"), ("P577", "Publication"),
    ("P1619", "Inauguration"), ("P1191", "Première représentation"),
]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


def _roman(n):
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
            (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def format_time(t, prec):
    m = re.match(r"([+-])(\d+)-(\d\d)-(\d\d)", t or "")
    if not m:
        return None
    bc = m.group(1) == "-"
    y, mo, d = int(m.group(2)), int(m.group(3)), int(m.group(4))
    suf = " av. J.-C." if bc else ""
    if prec >= 11 and mo and d:
        return f"{'1er' if d == 1 else d} {MOIS[mo - 1]} {y}{suf}"
    if prec == 10 and mo:
        return f"{MOIS[mo - 1]} {y}{suf}"
    if prec == 9:
        return f"{y}{suf}"
    if prec == 8:
        return f"années {y // 10 * 10}{suf}"
    if prec == 7:
        return f"{_roman((y - 1) // 100 + 1)}e siècle{suf}"
    if prec == 6:
        return f"{_roman((y - 1) // 1000 + 1)}e millénaire{suf}"
    return f"{y}{suf}"


def _time_of(snak):
    dv = (snak or {}).get("datavalue")
    if not dv or dv.get("type") != "time":
        return None
    return dv["value"].get("time"), dv["value"].get("precision", 9)


def _sortkey(t):
    m = re.match(r"([+-])(\d+)-(\d\d)-(\d\d)", t or "")
    if not m:
        return (10 ** 9, 0, 0)
    y = int(m.group(2)) * (-1 if m.group(1) == "-" else 1)
    return (y, int(m.group(3)), int(m.group(4)))


def _best(statements):
    st = [c for c in statements if c.get("rank") != "deprecated"]
    pref = [c for c in st if c.get("rank") == "preferred"]
    return pref or st


def _qual_time(c, *pids):
    for pid in pids:
        for q in c.get("qualifiers", {}).get(pid, []):
            t = _time_of(q)
            if t:
                return t
    return None


def _entity_id(c):
    dv = c.get("mainsnak", {}).get("datavalue")
    if dv and dv.get("type") == "wikibase-entityid":
        return dv["value"].get("id")
    return None


def _wd_entities(ids, props):
    out = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 50):
        r = _session.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetentities", "ids": "|".join(ids[i:i + 50]), "props": props,
            "languages": "fr|en", "languagefallback": 1, "format": "json"}, timeout=25)
        r.raise_for_status()
        out.update(r.json().get("entities", {}))
    return out


def _label(ent):
    labels = (ent or {}).get("labels", {})
    for lang in ("fr", "en"):
        if lang in labels:
            return labels[lang]["value"]
    return None


MAX_DATES = 16


def fetch_wikidata(qid):
    """Dates clés : dates propres à l'élément, puis événements marquants, œuvres et fonctions."""
    ent = _wd_entities([qid], "claims").get(qid, {})
    claims = ent.get("claims", {})
    dates, seen = [], set()

    def add(t, label):
        if not t:
            return
        txt = format_time(*t)
        if txt and (txt, label) not in seen:
            seen.add((txt, label))
            dates.append({"label": label, "date": txt, "sort": t[0]})

    for pid, label in DATE_PROPS:
        for c in _best(claims.get(pid, []))[:2]:
            add(_time_of(c.get("mainsnak")), label)

    # Éléments liés : événements marquants (P793), œuvres (P800), fonctions (P39)
    events = [(c, _entity_id(c)) for c in _best(claims.get("P793", []))[:8]]
    works = [_entity_id(c) for c in _best(claims.get("P800", []))[:8]]
    posts = [(c, _entity_id(c)) for c in _best(claims.get("P39", []))[:8]]
    ids = [i for _, i in events if i] + [w for w in works if w] + [i for _, i in posts if i]
    linked = {}
    if ids:
        try:
            linked = _wd_entities(ids, "labels|claims")
        except Exception:  # noqa: BLE001
            linked = {}

    for c, i in events:
        name = _label(linked.get(i))
        t = _qual_time(c, "P585", "P580")
        if not t and i in linked:
            for pid in ("P585", "P580", "P571"):
                st = _best(linked[i].get("claims", {}).get(pid, []))
                if st and _time_of(st[0].get("mainsnak")):
                    t = _time_of(st[0]["mainsnak"])
                    break
        if name:
            add(t, f"Événement : {name}")
    for i in works:
        e = linked.get(i)
        name = _label(e)
        if not name:
            continue
        for pid in ("P577", "P571", "P1191"):
            st = _best(e.get("claims", {}).get(pid, []))
            if st and _time_of(st[0].get("mainsnak")):
                add(_time_of(st[0]["mainsnak"]), f"Œuvre : {name}")
                break
    for c, i in posts:
        name = _label(linked.get(i))
        start, stop = _qual_time(c, "P580"), _qual_time(c, "P582")
        if not name or not start:
            continue
        a = format_time(*start)
        txt = f"{a} – {format_time(*stop)}" if stop else a
        if (txt, name) not in seen:
            seen.add((txt, name))
            dates.append({"label": f"Fonction : {name}", "date": txt, "sort": start[0]})

    dates.sort(key=lambda d: _sortkey(d["sort"]))
    if len(dates) > MAX_DATES:
        core = {lab for _, lab in DATE_PROPS}
        keep = [d for d in dates if d["label"] in core]
        rest = [d for d in dates if d["label"] not in core][:MAX_DATES - len(keep)]
        dates = sorted(keep + rest, key=lambda d: _sortkey(d["sort"]))

    coords = None
    for c in claims.get("P625", []):
        dv = c.get("mainsnak", {}).get("datavalue")
        if dv and str(dv["value"].get("globe", "")).endswith("Q2"):
            coords = {"lat": dv["value"]["latitude"], "lon": dv["value"]["longitude"]}
            break
    return {"dates": dates, "coords": coords}


# --- Lieux ----------------------------------------------------------------

def geocode(query):
    """Nominatim (OpenStreetMap), une seule requête, User-Agent identifié."""
    r = _session.get("https://nominatim.openstreetmap.org/search", params={
        "q": query, "format": "jsonv2", "limit": 1, "accept-language": "fr"}, timeout=15)
    r.raise_for_status()
    d = r.json()
    if not d:
        return None
    h = d[0]
    return {"lat": float(h["lat"]), "lon": float(h["lon"]), "name": h.get("name") or query,
            "description": f"{h.get('addresstype') or h.get('type', '')} {h.get('display_name', '')}"}


def locate(name):
    """Coordonnées d'un lieu : article Wikipédia d'abord, sinon OpenStreetMap."""
    try:
        s = fetch_summary("wikipedia", name)
    except Exception:  # noqa: BLE001
        s = None
    if s and s.get("coords"):
        return {"lat": s["coords"]["lat"], "lon": s["coords"]["lon"], "name": s["title"],
                "description": s.get("description", "")}
    return geocode(name)


# --- Wiktionnaire ----------------------------------------------------------

def fetch_wiktionary(word):
    for w in dict.fromkeys((word, word.lower())):
        r = _session.get(f"https://fr.wiktionary.org/api/rest_v1/page/html/{quote_title(w)}", timeout=10)
        if r.status_code == 200:
            return w, _body(r.text)
    return word, None


# --- Commons ---------------------------------------------------------------

def _file_info(p):
    ii = p["imageinfo"][0]
    md = ii.get("extmetadata", {})

    def g(k):
        return strip_tags(md.get(k, {}).get("value", ""))

    return {
        "title": p["title"],
        "name": p["title"].split(":", 1)[-1],
        "thumb": ii.get("thumburl") or ii.get("url"),
        "url": ii.get("url"),
        "page": ii.get("descriptionurl"),
        "width": ii.get("width"), "height": ii.get("height"),
        "author": g("Artist"), "license": g("LicenseShortName"),
        "description": g("ImageDescription") or g("ObjectName"),
    }


_II = {"prop": "imageinfo", "iiprop": "url|size|extmetadata",
       "iiextmetadatafilter": "Artist|LicenseShortName|ImageDescription|ObjectName",
       "iiextmetadatalanguage": "fr", "format": "json"}


def commons_search(query, limit=30):
    # Grille : URL et taille seulement (les métadonnées, lentes, sont lues dans le détail).
    params = {"action": "query", "format": "json", "generator": "search",
              "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": limit,
              "prop": "imageinfo", "iiprop": "url|size", "iiurlwidth": 240}
    r = _session.get("https://commons.wikimedia.org/w/api.php", params=params, timeout=25)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    items = sorted(pages.values(), key=lambda p: p.get("index", 0))
    return [_file_info(p) for p in items if p.get("imageinfo")]


def commons_file(title, width=1280):
    name = title.split(":", 1)[-1]
    params = dict(_II, action="query", titles=f"File:{name}", iiurlwidth=width)
    r = _session.get("https://commons.wikimedia.org/w/api.php", params=params, timeout=20)
    r.raise_for_status()
    for p in r.json().get("query", {}).get("pages", {}).values():
        if p.get("imageinfo"):
            return _file_info(p)
    raise NotFound(title)


def fetch_bytes(url):
    r = _session.get(https(url), timeout=60)
    r.raise_for_status()
    return r.content


def download_to(url, path):
    with _session.get(https(url), stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    return path
