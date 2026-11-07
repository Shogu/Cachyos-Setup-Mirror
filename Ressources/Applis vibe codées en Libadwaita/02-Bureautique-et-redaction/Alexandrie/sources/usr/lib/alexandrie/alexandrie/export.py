"""Export PDF (WeasyPrint) : fiche du panier et article mis en page."""

import html as _html

from . import api

PRINT_CSS = """
@page { size: A4; margin: 18mm 18mm 20mm; @bottom-center { content: counter(page); font-size: 8pt; color: #77767b; } }
body { font-family: "Source Serif 4", "Noto Serif", "DejaVu Serif", serif; font-size: 11pt; line-height: 1.5; color: #000; }
h1, h2, h3, h4 { font-family: "Adwaita Sans", "Cantarell", sans-serif; line-height: 1.25; page-break-after: avoid; }
h1 { font-size: 19pt; margin: 0 0 2mm; }
h2 { font-size: 14pt; margin: 7mm 0 2mm; border-bottom: 0.5pt solid #c0bfbc; padding-bottom: 1mm; }
h3 { font-size: 12pt; margin: 5mm 0 1.5mm; }
.desc { color: #5e5c64; margin: 0 0 6mm; font-family: "Adwaita Sans", sans-serif; }
a, span { color: inherit; text-decoration: none; }
img { max-width: 100%; height: auto; }
figure { margin: 3mm 0; page-break-inside: avoid; font-size: 8.5pt; color: #444; }
figure[typeof~="mw:File/Thumb"], figure[typeof~="mw:File/Frame"] { float: right; width: 62mm; margin: 0 0 3mm 5mm; }
figure img { max-height: 120mm; }
figcaption { margin-top: 1mm; }
.infobox_v2, .infobox_v3, table.infobox { float: right; width: 62mm; margin: 0 0 4mm 5mm; font-size: 8pt; }
.infobox_v2 *, .infobox_v3 * { background: none !important; }
table { border-collapse: collapse; font-size: 9pt; margin: 3mm 0; }
td, th { border: 0.5pt solid #9a9996; padding: 1mm 2mm; vertical-align: top; }
blockquote { border-left: 2pt solid #c0bfbc; margin: 3mm 0; padding-left: 4mm; color: #333; }
.toc { border: 0.5pt solid #c0bfbc; padding: 3mm 5mm; margin: 0 0 6mm; font-size: 10pt; }
.toc ul { margin: 0; padding-left: 5mm; } .toc li.l3 { margin-left: 5mm; list-style: circle; }
.credit { font-size: 8pt; color: #77767b; margin-top: 8mm; }
"""


def _fetch(url, *args, **kwargs):
    from weasyprint import default_url_fetcher
    if url.startswith("http"):
        r = api.session().get(url, timeout=30)
        r.raise_for_status()
        return {"string": r.content, "mime_type": r.headers.get("content-type", "").split(";")[0],
                "redirected_url": r.url}
    return default_url_fetcher(url, *args, **kwargs)


def wrap(body_html, title=None):
    t = f"<title>{_html.escape(title)}</title>" if title else ""
    return f'<!doctype html><html lang="fr"><head><meta charset="utf-8">{t}<style>{PRINT_CSS}</style></head><body>{body_html}</body></html>'


def article_document(title, description, body, toc=None, credit=None):
    esc = _html.escape
    parts = [f"<h1>{esc(title)}</h1>"]
    if description:
        parts.append(f'<p class="desc">{esc(description)}</p>')
    if toc:
        lis = "".join(f'<li class="l{i["level"]}">{esc(i["text"])}</li>' for i in toc)
        parts.append(f'<div class="toc"><b>Sommaire</b><ul>{lis}</ul></div>')
    parts.append(body)
    if credit:
        parts.append(f'<p class="credit">{esc(credit)}</p>')
    return wrap("".join(parts), title)


def write_pdf(document, path, base_url):
    from weasyprint import HTML
    HTML(string=document, base_url=base_url, url_fetcher=_fetch).write_pdf(path)
    return path
