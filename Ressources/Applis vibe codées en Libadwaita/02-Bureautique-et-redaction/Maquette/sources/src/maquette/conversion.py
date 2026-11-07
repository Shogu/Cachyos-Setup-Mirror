"""Conversion des images en pages PDF, à la volée.

Appelée uniquement depuis le fil du moteur. Renvoie un pymupdf.Document en
mémoire ; rien n'est écrit sur le disque.

Les documents de traitement de texte ne sont pas pris en charge : sans
LibreOffice, aucune conversion ne respecte la mise en page d'origine. Il faut
les exporter en PDF depuis leur éditeur, puis déposer le PDF ici.
"""

from __future__ import annotations

import io
import os

import pymupdf

from .modele import A4

EXT_PDF = {".pdf"}
EXT_IMAGES = {".png", ".jpg", ".jpeg", ".jpe", ".webp", ".gif", ".bmp",
              ".tif", ".tiff", ".avif", ".heic", ".heif", ".jxl", ".svg"}
# Formats qu'il faut exporter en PDF avant de les insérer ; les nommer permet
# d'expliquer pourquoi plutôt que d'afficher « format non pris en charge ».
EXT_BUREAUTIQUE = {".odt", ".ott", ".fodt", ".doc", ".docx", ".docm", ".dotx",
                   ".dotm", ".rtf", ".odp", ".pptx", ".ods", ".xlsx"}

MM = 72 / 25.4


class ErreurConversion(Exception):
    """Message destiné à l'utilisateur, en français."""


def genre_fichier(chemin: str) -> str | None:
    ext = os.path.splitext(chemin)[1].lower()
    if ext in EXT_PDF:
        return "pdf"
    if ext in EXT_IMAGES:
        return "image"
    if ext in EXT_BUREAUTIQUE:
        return "bureautique"
    # sans extension connue : on regarde le début du fichier
    try:
        with open(chemin, "rb") as f:
            tete = f.read(16)
    except OSError:
        return None
    if tete.startswith(b"%PDF"):
        return "pdf"
    if tete[:8] == b"\x89PNG\r\n\x1a\n" or tete[:3] == b"\xff\xd8\xff":
        return "image"
    return None


# -------------------------------------------------------------------- images

def _par_pillow(chemin: str):
    """→ (octets PNG ou JPEG, largeur, hauteur), orientation EXIF appliquée."""
    from PIL import Image, ImageOps
    with Image.open(chemin) as im:
        im.seek(0)
        orientation = im.getexif().get(0x0112, 1)
        format_origine = im.format
        if orientation in (None, 1) and format_origine in ("JPEG", "PNG"):
            with open(chemin, "rb") as f:            # repris tel quel, sans perte
                return f.read(), im.width, im.height
        redresse = ImageOps.exif_transpose(im)
        sortie = io.BytesIO()
        transparente = (redresse.mode in ("RGBA", "LA", "P", "PA")
                        or format_origine in ("PNG", "GIF", "BMP", "TIFF"))
        if transparente:
            if redresse.mode not in ("RGB", "RGBA", "L", "LA"):
                redresse = redresse.convert("RGBA")
            redresse.save(sortie, "PNG", optimize=True)
        else:
            redresse.convert("RGB").save(sortie, "JPEG", quality=92)
        return sortie.getvalue(), redresse.width, redresse.height


def _par_gdk(chemin: str):
    """Repli par les chargeurs de GTK : SVG, HEIC, AVIF, JXL…"""
    from gi.repository import Gdk
    texture = Gdk.Texture.new_from_filename(chemin)
    return texture.save_to_png_bytes().get_data(), texture.get_width(), texture.get_height()


def _charger_image(chemin: str):
    """Pillow d'abord, puis les chargeurs de GTK pour les formats qu'il ignore."""
    lecteurs = (_par_gdk,) if chemin.lower().endswith(".svg") else (_par_pillow, _par_gdk)
    for lecteur in lecteurs:
        try:
            return lecteur(chemin)
        except Exception:
            continue
    raise ErreurConversion(f"Impossible de lire l'image « {os.path.basename(chemin)} ».")


def image_vers_pdf(chemin: str, marges_mm: float, pleine_page: bool,
                   orientation_auto: bool) -> pymupdf.Document:
    donnees, il, ih = _charger_image(chemin)
    pl, ph = A4
    if orientation_auto and il > ih:
        pl, ph = ph, pl
    m = 0 if pleine_page else max(0.0, marges_mm) * MM
    doc = pymupdf.open()
    page = doc.new_page(width=pl, height=ph)
    page.insert_image(pymupdf.Rect(m, m, pl - m, ph - m), stream=donnees,
                      keep_proportion=True)
    doc.set_metadata({"title": os.path.basename(chemin)})
    return doc
