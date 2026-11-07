#!/bin/bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
VER=1.1.1
REL=1
OUT=/tmp/claude-0/pkgroot
rm -rf "$OUT"; mkdir -p "$OUT"

install -d "$OUT/usr/lib/maquette/maquette" "$OUT/usr/bin" \
           "$OUT/usr/share/applications" "$OUT/usr/share/metainfo" \
           "$OUT/usr/share/glib-2.0/schemas" "$OUT/usr/share/doc/maquette"
install -m644 "$SRC"/maquette/*.py "$OUT/usr/lib/maquette/maquette/"
install -m644 "$SRC"/maquette/style.css "$OUT/usr/lib/maquette/maquette/"
install -m755 "$SRC"/data/maquette.sh "$OUT/usr/bin/maquette"
install -m644 "$SRC"/data/io.gitlab.shogu.Maquette.desktop "$OUT/usr/share/applications/"
install -m644 "$SRC"/data/io.gitlab.shogu.Maquette.metainfo.xml "$OUT/usr/share/metainfo/"
install -m644 "$SRC"/data/io.gitlab.shogu.Maquette.gschema.xml "$OUT/usr/share/glib-2.0/schemas/"
for d in scalable/apps symbolic/apps 128x128/apps scalable/actions; do
  install -d "$OUT/usr/share/icons/hicolor/$d"
  install -m644 "$SRC/data/icons/hicolor/$d/"* "$OUT/usr/share/icons/hicolor/$d/"
done
install -m644 "$SRC/README.md" "$OUT/usr/share/doc/maquette/" 2>/dev/null || true

TAILLE=$(du -sb "$OUT" | cut -f1)
cat > "$OUT/.PKGINFO" <<PKG
# Généré pour Maquette $VER-$REL
pkgname = maquette
pkgbase = maquette
pkgver = $VER-$REL
pkgdesc = Assembler et préparer des documents PDF (GTK4/libadwaita)
url = https://gitlab.com/shogu/maquette
builddate = $(date +%s)
packager = Maquette <maquette@localhost>
size = $TAILLE
arch = any
license = AGPL-3.0-or-later
depend = python
depend = python-gobject
depend = python-cairo
depend = gtk4
depend = libadwaita
depend = python-pymupdf
depend = python-pillow
depend = hicolor-icon-theme
PKG

cd "$OUT"
LANG=C bsdtar -czf .MTREE --format=mtree \
  --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' \
  .PKGINFO usr
LANG=C bsdtar -cf - .PKGINFO .MTREE usr | zstd -q -19 -T0 -o "/tmp/claude-0/maquette-$VER-$REL-any.pkg.tar.zst" -f
echo "paquet : $(du -h /tmp/claude-0/maquette-$VER-$REL-any.pkg.tar.zst | cut -f1)"
