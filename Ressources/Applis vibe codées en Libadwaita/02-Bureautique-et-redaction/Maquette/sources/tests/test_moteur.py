"""Tests du moteur, sans interface : python3 -m pytest tests/ (depuis la racine)."""

import os
import sys
from dataclasses import replace

import pymupdf
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from maquette import modele  # noqa: E402
from maquette.modele import EFFACER, ROGNER, SUPPRIMER, TEXTE, Op, Page, Source  # noqa: E402
from maquette.moteur import Moteur  # noqa: E402

REGLAGES = {
    "images_marges": 10, "images_mode": "ajustee", "images_orientation_auto": True,
    "imposition": "fidele", "compresser": True,
    "reduire_images": False, "dpi_images": 150, "effacer_metadonnees": False,
}


def pdf_essai(chemin, n=3, rotation=0, taille=(595, 842)):
    doc = pymupdf.open()
    for i in range(n):
        p = doc.new_page(width=taille[0], height=taille[1])
        for k in range(10):
            p.insert_text((50, 60 + k * 70), f"page{i} ligne{k} HAUT" if k < 5 else f"page{i} ligne{k} BAS", fontsize=14)
        p.draw_rect(pymupdf.Rect(10, 10, 60, 40), color=(1, 0, 0), fill=(1, 0, 0))
        p.set_rotation(rotation)
    doc.set_metadata({"title": "Essai", "author": "Prof"})
    doc.save(chemin)
    return chemin


@pytest.fixture
def moteur():
    return Moteur(planifier=lambda f, *a: f(*a))


def ouvrir(m, chemin):
    sid = modele.nouvel_id_source()
    infos = m.ouvrir(sid, chemin, "pdf", REGLAGES)
    return {sid: Source(sid, os.path.basename(chemin), chemin, "pdf", infos)}, sid


def texte(doc_or_page):
    return doc_or_page.get_text()


def test_geometrie_suit_le_moteur(moteur, tmp_path):
    for rot in (0, 90, 180, 270):
        sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / f"r{rot}.pdf"), 1, rot))
        page = Page(modele.nouvel_uid(), sid, 0, rotation=90)
        ops = [
            ("effacer", 0.1, 0.1, 0.4, 0.3),
            ("supprimer", 0.0, 0.5, 1.0, 0.6),
            ("rogner", 0.05, 0.05, 0.8, 0.7),
        ]
        for genre, *f in ops:
            op = modele.zone_depuis_affichage(page, sources, genre, *f)
            assert op is not None
            page = replace(page, ops=page.ops + (op,))
            l, h = modele.taille_intermediaire(page, sources)
            d = moteur.page_unique(page)[0]
            assert abs(d.rect.width - l) < 0.6 and abs(d.rect.height - h) < 0.6, (rot, genre)
        w, hh, _, _ = moteur.rendre(page, 400, 400)
        dl, dh = modele.taille_affichee(page, sources)
        assert abs(w / hh - dl / dh) < 0.03


def test_vers_non_tourne_correspond_a_pymupdf():
    doc = pymupdf.open()
    p = doc.new_page(width=200, height=100)
    for r in (0, 90, 180, 270):
        p.set_rotation(r)
        m = p.derotation_matrix
        for u, v in ((10, 20), (55, 5), (0, 0)):
            attendu = pymupdf.Point(u, v) * m
            x, y = modele.vers_non_tourne(u, v, 200, 100, r)
            assert abs(attendu.x - x) < 1e-6 and abs(attendu.y - y) < 1e-6, r


def test_effacer_retire_le_texte(moteur, tmp_path):
    sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    page = Page(1, sid, 0, ops=(Op(EFFACER, 0, 0, 595, 400),))
    t = texte(moteur.page_unique(page)[0])
    assert "HAUT" not in t and "BAS" in t


def test_supprimer_passage_remonte_la_suite(moteur, tmp_path):
    sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    page = Page(1, sid, 0, ops=(Op(SUPPRIMER, 0, 100, 595, 400, axe="y"),))
    p = moteur.page_unique(page)[0]
    assert abs(p.rect.height - (842 - 300)) < 0.5
    t = p.get_text()
    for k in (0, 6, 9):
        assert f"ligne{k} " in t
    for k in (1, 2, 3, 4, 5):
        assert f"ligne{k} " not in t
    # la ligne 6 (y≈480 à l'origine) est remontée de 300 pt
    zone = p.search_for("ligne6")[0]
    assert 160 < zone.y0 < 190


def test_rogner(moteur, tmp_path):
    sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    page = Page(1, sid, 0, ops=(Op(ROGNER, 0, 0, 400, 200),))
    p = moteur.page_unique(page)[0]
    assert (round(p.rect.width), round(p.rect.height)) == (400, 200)
    assert "ligne0" in p.get_text() and "ligne5" not in p.get_text()
    page2 = Page(2, sid, 0, ops=(Op(ROGNER, 0, 0, 400, 200, garder_format=True),))
    p2 = moteur.page_unique(page2)[0]
    assert round(p2.rect.height) == 842 and "ligne5" not in p2.get_text()


def test_enregistrer_fusion_rotation_et_ecriture_atomique(moteur, tmp_path):
    s1, a = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 3))
    s2, b = ouvrir(moteur, pdf_essai(str(tmp_path / "b.pdf"), 2, rotation=90))
    pages = [Page(1, a, 2), Page(2, b, 0, rotation=90), Page(3, a, 0),
             Page(4, None, blanche=(595, 842)), Page(5, b, 1, ops=(Op(EFFACER, 0, 0, 300, 300),))]
    sortie = tmp_path / "sortie.pdf"
    taille = moteur.enregistrer(pages, str(sortie), REGLAGES, {a: "pdf", b: "pdf"})
    assert taille == os.path.getsize(sortie)
    d = pymupdf.open(sortie)
    assert d.page_count == 5
    assert "page2" in d[0].get_text() and "page0" in d[2].get_text()
    assert d[1].rotation == 180 and d[4].rotation == 90
    assert d[3].get_text().strip() == ""
    assert d.metadata["title"] == "Essai" and d.metadata["creator"] == "Maquette"
    assert not [f for f in os.listdir(tmp_path) if f.startswith(".maquette-")]


def test_remplacer_un_original_ouvert(moteur, tmp_path):
    chemin = pdf_essai(str(tmp_path / "a.pdf"), 3)
    s, a = ouvrir(moteur, chemin)
    moteur.enregistrer([Page(1, a, 2), Page(2, a, 0)], chemin, REGLAGES, {a: "pdf"})
    d = pymupdf.open(chemin)
    assert d.page_count == 2 and "page2" in d[0].get_text()


def test_metadonnees_effacees(moteur, tmp_path):
    s, a = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    r = dict(REGLAGES, effacer_metadonnees=True)
    moteur.enregistrer([Page(1, a, 0)], str(tmp_path / "s.pdf"), r, {a: "pdf"})
    assert not pymupdf.open(tmp_path / "s.pdf").metadata["author"]


def test_image_paysage(moteur, tmp_path):
    from PIL import Image
    Image.new("RGB", (1600, 900), "#3584e4").save(tmp_path / "i.webp")
    infos = moteur.ouvrir(99, str(tmp_path / "i.webp"), "image", REGLAGES)
    l, h, _ = infos[0]
    assert l > h


def test_bureautique_refusee_avec_une_consigne(moteur, tmp_path):
    from maquette import conversion
    (tmp_path / "cours.odt").write_bytes(b"PK\x03\x04")
    with pytest.raises(conversion.ErreurConversion, match="exporté en PDF"):
        moteur.ouvrir(90, str(tmp_path / "cours.odt"), "bureautique", REGLAGES)


def test_texte_ne_depasse_jamais_de_la_page(moteur, tmp_path):
    """Un cadre agrandi reste dans la page, sans calque de texte coupé."""
    sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    page = Page(1, sid, 0, ops=(Op(TEXTE, 60, 700, 520, 760, contenu="Mot " * 300, taille=20),))
    rendu = moteur.page_unique(page)[0]
    for bloc in rendu.get_text("blocks"):
        assert bloc[3] <= rendu.rect.y1 + 1


def test_texte_pose_sur_la_page(moteur, tmp_path):
    sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    phrase = "Corrigé — séance 3 : l'élève écrit « à é è ç ù œ »."
    page = Page(1, sid, 0, ops=(Op(TEXTE, 60, 500, 500, 600, contenu=phrase,
                                   taille=13, couleur="#e01b24"),))
    doc = moteur.page_unique(page)
    assert phrase in doc[0].get_text().replace("\n", " ")
    # le texte s'ajoute sans toucher au format ni au contenu d'origine
    assert round(doc[0].rect.height) == 842 and "ligne0" in doc[0].get_text()


def test_texte_reduit_le_corps_s_il_deborde(moteur, tmp_path):
    sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    long_texte = "Phrase de contrôle. " * 40
    page = Page(1, sid, 0, ops=(Op(TEXTE, 60, 60, 300, 160, contenu=long_texte, taille=24),))
    rendu = " ".join(moteur.page_unique(page)[0].get_text().split())
    assert rendu.count("Phrase de contrôle.") == 40, "du texte a été perdu"


def test_les_trois_issues_du_recadrage(moteur, tmp_path):
    """Garder la zone, la vider, ou la retirer en réduisant la page."""
    sources, sid = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 1))
    zone = (0, 100, 595, 400)
    garder = moteur.page_unique(Page(1, sid, 0, ops=(Op(ROGNER, *zone),)))[0]
    vider = moteur.page_unique(Page(2, sid, 0, ops=(Op(EFFACER, *zone),)))[0]
    retirer = moteur.page_unique(Page(3, sid, 0, ops=(Op(SUPPRIMER, *zone, axe="y"),)))[0]

    assert round(garder.rect.height) == 300 and "ligne1" in garder.get_text()
    assert round(vider.rect.height) == 842 and "ligne1" not in vider.get_text()
    assert round(retirer.rect.height) == 542 and "ligne1" not in retirer.get_text()
    # seule la dernière remonte le contenu resté sous la zone
    assert vider.search_for("ligne6")[0].y0 > retirer.search_for("ligne6")[0].y0


def test_livret_a5_dans_l_ordre_d_impression(moteur, tmp_path):
    from maquette.moteur import ordre_livret
    assert ordre_livret(4) == [(3, 0), (1, 2)]
    assert ordre_livret(5) == [(None, 0), (1, None), (None, 2), (3, 4)]

    s, a = ouvrir(moteur, pdf_essai(str(tmp_path / "a.pdf"), 4))
    pages = [Page(i + 1, a, i) for i in range(4)]
    sortie = tmp_path / "livret.pdf"
    moteur.enregistrer(pages, str(sortie), dict(REGLAGES, imposition="brochure-a5"), {a: "pdf"})
    d = pymupdf.open(sortie)
    assert d.page_count == 2
    assert (round(d[0].rect.width), round(d[0].rect.height)) == (842, 595)
    assert "page3" in d[0].get_text() and "page0" in d[0].get_text()
    assert "page1" in d[1].get_text() and "page2" in d[1].get_text()
