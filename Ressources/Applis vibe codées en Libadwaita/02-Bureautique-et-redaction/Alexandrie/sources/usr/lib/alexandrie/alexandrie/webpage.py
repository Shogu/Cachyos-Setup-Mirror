"""Gabarit HTML de lecture : feuille de style et script injectés dans WebKitGTK."""

import html as _html
import json

CSS = r"""
:root{--bg:#ffffff;--fg:#1e1e1e;--muted:#5e5c64;--accent:#1c71d8;--line:#deddda;--card:#f6f5f4}
body.dark{--bg:#1d1d20;--fg:#ffffff;--muted:#c0bfbc;--accent:#78aeed;--line:#3d3846;--card:#2a2a2e}
html,body{background:var(--bg);color:var(--fg)}
body{margin:0;font:17px/1.65 "Source Serif 4","Noto Serif","DejaVu Serif",Georgia,serif;-webkit-font-smoothing:antialiased}
article{max-width:46em;margin:0 auto;padding:28px 36px 96px}
body.w-wide article{max-width:64em}
body.w-full article{max-width:none;padding-left:56px;padding-right:56px}
h1,h2,h3,h4,h5{font-family:"Adwaita Sans","Cantarell","Inter",sans-serif;font-weight:700;line-height:1.25}
h1{font-size:2em;margin:0 0 .15em}
.alex-desc{color:var(--muted);font-family:"Adwaita Sans","Cantarell",sans-serif;margin:0 0 1.4em}
h2{font-size:1.45em;border-bottom:1px solid var(--line);padding-bottom:.2em;margin-top:1.8em}
h3{font-size:1.18em;margin-top:1.4em}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
a.new{color:inherit;pointer-events:none}
img{max-width:100%;height:auto;border-radius:6px}
figure{margin:.3em 0 1em 1.6em;float:right;clear:right;max-width:300px;font:.8em/1.4 "Adwaita Sans","Cantarell",sans-serif;color:var(--muted)}
figure[typeof~="mw:File"],figure[typeof~="mw:File/Frameless"]{float:none;margin:1em 0;max-width:100%}
figure[typeof~="mw:File/Thumb"],figure[typeof~="mw:File/Frame"]{float:right;margin:.3em 0 1em 1.6em;max-width:300px}
span[typeof~="mw:File"] img{vertical-align:middle;border-radius:0}
figcaption{margin-top:.3em}
.infobox_v2,.infobox_v3,table.infobox,.infobox{float:right;clear:right;width:300px;margin:0 0 1em 1.6em;font:.8em/1.45 "Adwaita Sans","Cantarell",sans-serif;background:var(--card);border-radius:12px;padding:8px;border:0}
.infobox_v3 *, .infobox_v2 *{background-color:transparent!important;border-color:var(--line)!important;color:inherit}
table{border-collapse:collapse;font-size:.88em;margin:1em 0}
td,th{border:1px solid var(--line);padding:4px 7px;vertical-align:top}
.infobox_v2 td,.infobox_v2 th,.infobox_v3 td{border:0}
blockquote{border-left:3px solid var(--line);margin:1em 0;padding:0 1.1em;color:var(--muted)}
.poem,.poeme{font-style:italic}
::selection{background:#3584e455}
@media (max-width:760px){article{padding:20px 18px 80px}figure,figure[typeof~="mw:File/Thumb"],.infobox_v2,.infobox_v3,table.infobox{float:none;margin:1em auto;width:auto;max-width:100%}}
"""

JS = r"""
(function(){
const A = window.ALEX;
function post(o){ window.webkit.messageHandlers.alex.postMessage(JSON.stringify(o)); }
const art = document.getElementById('alex-article');

const KILL = ['.navbox','.navbox-container','.bandeau-container','.bandeau-portail','#bandeau-portail',
  '.homonymie','.metadata','.noprint','.mw-editsection','.mw-empty-elt','link','style','meta',
  '.autres-projets','.ambox','.bandeau','.ws-noexport','.mw-kartographer-maplink','.printfooter',
  '#toc','.toc','.mw-jump-link','.catlinks'];
const REFS = ['sup.reference','.mw-ref','.reference','.mw-references-wrap','.references','.mw-cite-backlink'];
const DROP_SECTIONS = /^(notes( et références)?|références|liens externes|voir aussi|bibliographie|annexes|articles connexes|sources|notes et sources)$/i;

/* Liens internes : Parsoid (rel="mw:WikiLink", href="./Titre") ou HTML classique (href="/wiki/Titre") */
function isWikiLink(a){
  if (!a || a.classList.contains('new') || a.classList.contains('external') || a.querySelector('img')) return false;
  const h = a.getAttribute('href') || '';
  if (h.startsWith('#')) return false;
  if ((a.getAttribute('rel') || '').includes('mw:WikiLink')) return true;
  try { return new URL(a.href).pathname.startsWith('/wiki/'); } catch (_) { return false; }
}
function wikiLinkAt(t){
  let a = t && t.closest ? t.closest('a') : null;
  return isWikiLink(a) ? a : null;
}

/* Section « Voir aussi » : contenu d'une section h2 (Parsoid : <section>, classique : frères suivants) */
const RELATED = /^(voir aussi|articles connexes|articles liés|liens internes)$/i;
function sectionNodes(h){
  if (h.parentElement && h.parentElement.tagName === 'SECTION' && h.parentElement.firstElementChild === h)
    return [h.parentElement];
  const block = (h.parentElement && h.parentElement.classList.contains('mw-heading')) ? h.parentElement : h;
  const out = []; let n = block.nextElementSibling;
  while (n && !(n.tagName === 'H2' || (n.classList && n.classList.contains('mw-heading2')))) { out.push(n); n = n.nextElementSibling; }
  return out;
}
function headingText(h){ return h.textContent.replace(/\[modifier[^\]]*\]/g, '').trim(); }
(function collectRelated(){
  const items = [], seen = new Set();
  art.querySelectorAll('h2').forEach(h => {
    if (!RELATED.test(headingText(h))) return;
    sectionNodes(h).forEach(n => n.querySelectorAll('a').forEach(a => {
      if (!isWikiLink(a)) return;
      let title;
      try { title = decodeURIComponent(new URL(a.href).pathname.replace(/^\/wiki\//, '')).replace(/_/g, ' '); }
      catch (_) { return; }
      if (title.includes(':') || seen.has(title)) return;
      seen.add(title); items.push({title: title, href: a.href});
    }));
  });
  post({type:'related', items: items.slice(0, 15)});
})();

function clean(){
  KILL.forEach(s => art.querySelectorAll(s).forEach(n => n.remove()));
  if (A.hideRefs){
    REFS.forEach(s => art.querySelectorAll(s).forEach(n => n.remove()));
    art.querySelectorAll('h2').forEach(h => {
      if (!DROP_SECTIONS.test(headingText(h))) return;
      sectionNodes(h).forEach(n => n.remove());
      const block = (h.parentElement && h.parentElement.classList.contains('mw-heading')) ? h.parentElement : h;
      if (block.isConnected) block.remove();
    });
  }
  art.querySelectorAll('[style*="display:none"],[style*="display: none"]').forEach(n => n.remove());
}
clean();
document.body.classList.toggle('dark', !!A.dark);

/* Sommaire */
const toc = []; let n = 0;
art.querySelectorAll('h2, h3').forEach(h => {
  if (!h.textContent.trim()) return;
  if (!h.id) h.id = 'alex-h' + (n++);
  toc.push({level: h.tagName === 'H2' ? 2 : 3, text: h.textContent.trim(), id: h.id});
});
post({type:'toc', items: toc});
if (toc.length && 'IntersectionObserver' in window){
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) post({type:'toc-active', id: e.target.id});
  }), {rootMargin: '0px 0px -75% 0px'});
  toc.forEach(t => { const el = document.getElementById(t.id); if (el) io.observe(el); });
}
window.alexScrollTo = id => { const el = document.getElementById(id); if (el) el.scrollIntoView({behavior:'smooth', block:'start'}); };
window.alexSetDark = b => document.body.classList.toggle('dark', b);
window.alexSetWidth = w => { document.body.classList.remove('w-wide', 'w-full'); if (w !== 'normal') document.body.classList.add('w-' + w); };
window.alexSetCopyMode = m => { A.copyMode = m; };

/* Nettoyage d'une sélection pour la copie et le panier */
const KEEP = new Set(['H1','H2','H3','H4','H5','H6','P','B','STRONG','I','EM','U','UL','OL','LI','BR',
  'BLOCKQUOTE','SUB','SUP','DL','DT','DD','TABLE','THEAD','TBODY','TR','TD','TH']);
const DROP = new Set(['IMG','FIGURE','FIGCAPTION','STYLE','SCRIPT','LINK','META','SVG','MATH','AUDIO','VIDEO','BUTTON']);
function sanitizeNode(src, dst){
  src.childNodes.forEach(c => {
    if (c.nodeType === 3){ dst.appendChild(document.createTextNode(c.textContent)); return; }
    if (c.nodeType !== 1) return;
    const t = c.tagName;
    if (DROP.has(t) || (c.classList && (c.classList.contains('reference') || c.classList.contains('mw-ref')))) return;
    if (KEEP.has(t)){ const e = document.createElement(t.toLowerCase()); sanitizeNode(c, e); dst.appendChild(e); }
    else sanitizeNode(c, dst);
  });
}
function sanitize(node){ const d = document.createElement('div'); sanitizeNode(node, d); return d; }
function toPlain(node){
  let out = '';
  (function walk(nd){
    nd.childNodes.forEach(c => {
      if (c.nodeType === 3){ out += c.textContent.replace(/\s+/g, ' '); return; }
      if (c.nodeType !== 1) return;
      const t = c.tagName;
      if (/^(H[1-6]|P|BLOCKQUOTE|DT|DD|TR|TABLE)$/.test(t)){ out += '\n\n'; walk(c); out += '\n\n'; }
      else if (t === 'LI'){ out += '\n• '; walk(c); }
      else if (t === 'BR'){ out += '\n'; }
      else if (t === 'TD' || t === 'TH'){ walk(c); out += '\t'; }
      else walk(c);
    });
  })(node);
  return out.replace(/[ \t]+\n/g, '\n').replace(/\n /g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}
const BLOCK = /^\s*<(h\d|p|ul|ol|blockquote|table|dl)\b/i;
function selPayload(){
  const s = getSelection();
  if (!s || s.isCollapsed || !s.rangeCount) return null;
  const d = sanitize(s.getRangeAt(0).cloneContents());
  let html = d.innerHTML.trim();
  if (!html) return null;
  if (!BLOCK.test(html)) html = '<p>' + html + '</p>';
  return {html: html, text: toPlain(d)};
}

/* Copie : Ctrl+C selon le réglage, Ctrl+Maj+C dans l'autre format */
let forceMode = null;
document.addEventListener('copy', e => {
  const p = selPayload(); if (!p) return;
  const mode = forceMode || A.copyMode;
  e.clipboardData.setData('text/plain', p.text);
  if (mode === 'rich') e.clipboardData.setData('text/html', p.html);
  e.preventDefault();
  post({type:'copied', mode: mode});
});
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.shiftKey && (e.key === 'C' || e.key === 'c')){
    forceMode = A.copyMode === 'rich' ? 'plain' : 'rich';
    document.execCommand('copy');
    forceMode = null;
    e.preventDefault();
  }
});

/* Images */
function imgInfo(img){
  const fig = img.closest('figure');
  let cap = '';
  if (fig){ const fc = fig.querySelector('figcaption'); if (fc) cap = fc.textContent; }
  if (!cap) cap = img.getAttribute('alt') || '';
  const a = img.closest('a');
  const res = img.getAttribute('resource') || (a && a.getAttribute('href')) || '';
  const m = decodeURIComponent(res).match(/(Fichier|File|Image):[^#?]+/);
  return {src: img.currentSrc || img.src, caption: cap.trim(), file: m ? m[0] : null};
}

/* Menu contextuel natif (Gtk.PopoverMenu côté Python) */
const WORD = /^[\p{L}’'\-]{2,40}$/u;
function cleanWord(w){ return w.trim().replace(/^[«"(]+|[»".,;:!?)]+$/g, '').replace(/^(?:[ldjmnstc]|qu)['’]/i, ''); }
document.addEventListener('contextmenu', e => {
  e.preventDefault();
  const img = e.target.closest('img');
  const sel = selPayload();
  const w = cleanWord(getSelection().toString());
  const link = wikiLinkAt(e.target);
  post({type:'context', x: e.clientX, y: e.clientY, sel: sel, word: WORD.test(w) ? w : null,
        img: img ? imgInfo(img) : null, seltext: getSelection().toString().trim(),
        link: (link && !img) ? {href: link.href, text: link.textContent.trim()} : null});
});

/* Liens */
document.addEventListener('click', e => {
  const a = e.target.closest('a'); if (!a) return;
  e.preventDefault();
  const href = a.getAttribute('href') || '';
  if (href.startsWith('#')){ alexScrollTo(decodeURIComponent(href.slice(1))); return; }
  const img = a.querySelector('img');
  if (img){ const info = imgInfo(img); if (info.file){ post({type:'open-file', file: info.file}); return; } }
  if (a.classList.contains('new')) return;
  post({type:'link', href: a.href, newtab: !!(e.ctrlKey || e.metaKey)});
});
/* Clic du milieu : nouvel onglet */
document.addEventListener('auxclick', e => {
  if (e.button !== 1) return;
  const a = wikiLinkAt(e.target); if (!a) return;
  e.preventDefault();
  post({type:'link', href: a.href, newtab: true});
});

/* Aperçu au survol */
if (A.linkPreview){
  let timer = null, current = null;
  const end = () => { clearTimeout(timer); if (current){ current = null; post({type:'hover-end'}); } };
  document.addEventListener('mouseover', e => {
    const a = wikiLinkAt(e.target);
    if (!a || a === current) return;
    end(); current = a;
    timer = setTimeout(() => {
      const r = a.getBoundingClientRect();
      post({type:'hover', href: a.href, x: r.left, y: r.top, w: r.width, h: r.height});
    }, 450);
  });
  document.addEventListener('mouseout', e => {
    if (!current) return;
    if (e.relatedTarget && current.contains(e.relatedTarget)) return;
    if (e.target.closest('a') === current) end();
  });
  document.addEventListener('scroll', end, {passive: true});
}

/* Wiktionnaire au double-clic */
if (A.dictionary){
  document.addEventListener('dblclick', e => {
    if (e.target.closest('a')) return;
    const s = getSelection(); if (!s.rangeCount) return;
    const w = cleanWord(s.toString());
    if (!WORD.test(w)) return;
    const r = s.getRangeAt(0).getBoundingClientRect();
    post({type:'define', word: w, x: r.left, y: r.top, w: r.width, h: r.height});
  });
}
window.alexDefineAt = function(word){
  const s = getSelection(); let r = {left: 40, top: 40, width: 1, height: 1};
  if (s.rangeCount) r = s.getRangeAt(0).getBoundingClientRect();
  post({type:'define', word: word, x: r.left, y: r.top, w: r.width, h: r.height});
};
window.alexParseDefinition = function(word, html){
  const doc = new DOMParser().parseFromString(html, 'text/html');
  let sec = null;
  doc.querySelectorAll('section').forEach(s => {
    if (sec) return;
    const h = s.firstElementChild;
    if (h && h.tagName === 'H2' && (h.querySelector('#fr') || /français/i.test(h.textContent))) sec = s;
  });
  const out = [];
  if (sec){
    sec.querySelectorAll('section').forEach(sub => {
      const h = sub.firstElementChild;
      if (!h || h.tagName !== 'H3') return;
      const ol = sub.querySelector(':scope > ol'); if (!ol) return;
      const defs = [];
      ol.querySelectorAll(':scope > li').forEach(li => {
        const c = li.cloneNode(true);
        c.querySelectorAll('ul, ol, dl, sup, .reference, style').forEach(x => x.remove());
        const t = c.textContent.replace(/\s+/g, ' ').trim();
        if (t) defs.push(t);
      });
      if (defs.length) out.push({pos: h.textContent.trim().replace(/\s*\d+$/, ''), defs: defs.slice(0, 4)});
    });
  }
  post({type:'definition', word: word, items: out.slice(0, 3)});
};

/* Article entier (copie, PDF) */
window.alexGetArticle = function(purpose, opts){
  opts = opts || {};
  const c = art.cloneNode(true);
  c.querySelectorAll('h1, .alex-desc').forEach(x => x.remove());
  const d = sanitize(c);
  if (opts.images === false){
    c.querySelectorAll('figure, img, .gallery, ul.gallery, .mw-gallery-traditional').forEach(x => x.remove());
  }
  c.querySelectorAll('a').forEach(a => { const s = document.createElement('span'); s.innerHTML = a.innerHTML; a.replaceWith(s); });
  c.querySelectorAll('img').forEach(i => { i.setAttribute('src', i.currentSrc || i.src); i.removeAttribute('srcset'); });
  post({type:'article', purpose: purpose, html: d.innerHTML, text: toPlain(d), full: c.innerHTML});
};

post({type:'ready'});
})();
"""


def build(site_host, title, description, body, *, dark, hide_refs, copy_mode, link_preview, dictionary,
          width="normal"):
    cfg = {"dark": dark, "hideRefs": hide_refs, "copyMode": copy_mode,
           "linkPreview": link_preview, "dictionary": dictionary}
    desc = f'<p class="alex-desc">{_html.escape(description)}</p>' if description else ""
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        f'<base href="https://{site_host}/wiki/">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<style>{CSS}</style></head>"
        f'<body class="{"dark" if dark else ""} w-{width}"><article id="alex-article">'
        f"<h1>{_html.escape(title)}</h1>{desc}{body}</article>"
        f"<script>window.ALEX = {json.dumps(cfg)};</script>"
        f"<script>{JS}</script></body></html>"
    )
