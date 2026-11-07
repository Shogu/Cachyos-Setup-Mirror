"""Exports PDF (cairo + Pango) et ODS. Aucune dépendance hors GTK/Pango/cairo."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo  # noqa: E402

from . import calculs, tableur  # noqa: E402
from .db import (CONVENTION, RECHERCHE, format_nombre, libelle_periode, normaliser,  # noqa: E402
                 nb_periodes, nom_complet)

A4 = (595.2756, 841.8898)
MARGE = 50
POLICE = "Adwaita Sans, Cantarell, Noto Sans, DejaVu Sans, sans-serif"

# Palette GNOME (documents imprimés : pas de CSS ici)
NOIR = (0.14, 0.12, 0.13)
GRIS = (0.37, 0.36, 0.39)
GRIS_CLAIR = (0.87, 0.87, 0.85)
FOND_ENTETE = (0.96, 0.96, 0.95)
BLEU = (0.11, 0.44, 0.85)


class Pdf:
    def __init__(self, chemin, titre: str):
        self.surface = cairo.PDFSurface(str(chemin), *A4)
        try:
            self.surface.set_metadata(cairo.PDFMetadata.TITLE, titre)
            self.surface.set_metadata(cairo.PDFMetadata.CREATOR, "Livret")
        except (AttributeError, cairo.Error):
            pass
        self.cr = cairo.Context(self.surface)
        self.titre_doc = titre
        self.page = 1
        self.y = MARGE
        self.largeur = A4[0] - 2 * MARGE
        self.bas = A4[1] - MARGE - 18

    # ----------------------------------------------------------- primitives
    def _layout(self, texte, taille=10.0, gras=False, italique=False, largeur=None,
                align=Pango.Alignment.LEFT):
        lay = PangoCairo.create_layout(self.cr)
        fd = Pango.FontDescription.from_string(POLICE)
        fd.set_size(int(taille * Pango.SCALE))
        if gras:
            fd.set_weight(Pango.Weight.BOLD)
        if italique:
            fd.set_style(Pango.Style.ITALIC)
        lay.set_font_description(fd)
        lay.set_width(int((largeur or self.largeur) * Pango.SCALE))
        lay.set_wrap(Pango.WrapMode.WORD_CHAR)
        lay.set_alignment(align)
        lay.set_text(texte or "", -1)
        return lay

    def _dessiner(self, lay, x, y, couleur=NOIR):
        self.cr.set_source_rgb(*couleur)
        self.cr.move_to(x, y)
        PangoCairo.show_layout(self.cr, lay)

    def _pied(self):
        lay = self._layout(f"{self.titre_doc} — page {self.page}", 7.5, largeur=self.largeur,
                           align=Pango.Alignment.CENTER)
        self._dessiner(lay, MARGE, A4[1] - MARGE + 6, GRIS)

    def nouvelle_page(self):
        self._pied()
        self.cr.show_page()
        self.page += 1
        self.y = MARGE

    def place(self, hauteur):
        if self.y + hauteur > self.bas and self.y > MARGE:
            self.nouvelle_page()

    def texte(self, texte, taille=10.0, gras=False, italique=False, couleur=NOIR, apres=4.0,
              retrait=0.0):
        lay = self._layout(texte, taille, gras, italique, self.largeur - retrait)
        # Les longs paragraphes sont coupés ligne par ligne entre les pages.
        it = lay.get_iter()
        lignes = []
        while True:
            _, logique = it.get_line_extents()
            lignes.append((logique.y / Pango.SCALE, logique.height / Pango.SCALE))
            if not it.next_line():
                break
        _, h = lay.get_pixel_size()
        if self.y + h <= self.bas or h < (self.bas - MARGE) / 3:
            self.place(h)
            self._dessiner(lay, MARGE + retrait, self.y, couleur)
            self.y += h + apres
            return
        decalage = 0.0
        for (ly, lh) in lignes:
            if self.y + (ly - decalage) + lh > self.bas:
                self.y += ly - decalage
                self.nouvelle_page()
                decalage = ly
            self.cr.save()
            self.cr.rectangle(MARGE + retrait - 2, self.y + ly - decalage, self.largeur, lh)
            self.cr.clip()
            self._dessiner(lay, MARGE + retrait, self.y - decalage, couleur)
            self.cr.restore()
        self.y += lignes[-1][0] + lignes[-1][1] - decalage + apres

    def deux_colonnes(self, gauche, droite, taille=10.0, gras=False, couleur_droite=GRIS, apres=4.0):
        lg = self._layout(gauche, taille, gras, largeur=self.largeur * 0.5)
        ld = self._layout(droite, taille, False, largeur=self.largeur * 0.5, align=Pango.Alignment.RIGHT)
        h = max(lg.get_pixel_size()[1], ld.get_pixel_size()[1])
        self.place(h)
        self._dessiner(lg, MARGE, self.y)
        self._dessiner(ld, MARGE + self.largeur * 0.5, self.y, couleur_droite)
        self.y += h + apres

    def filet(self, couleur=GRIS_CLAIR, epaisseur=0.8, avant=2.0, apres=8.0):
        self.y += avant
        self.cr.set_source_rgb(*couleur)
        self.cr.set_line_width(epaisseur)
        self.cr.move_to(MARGE, self.y)
        self.cr.line_to(MARGE + self.largeur, self.y)
        self.cr.stroke()
        self.y += apres

    def espace(self, h):
        self.y += h

    def entete(self, titre, sous_titre=""):
        self.cr.set_source_rgb(*BLEU)
        self.cr.rectangle(MARGE, self.y, 4, 30 if sous_titre else 20)
        self.cr.fill()
        lay = self._layout(titre, 17, True, largeur=self.largeur - 14)
        self._dessiner(lay, MARGE + 14, self.y - 3)
        self.y += lay.get_pixel_size()[1] - 2
        if sous_titre:
            lay = self._layout(sous_titre, 9.5, largeur=self.largeur - 14)
            self._dessiner(lay, MARGE + 14, self.y, GRIS)
            self.y += lay.get_pixel_size()[1]
        self.y += 16

    def tableau(self, entetes, lignes, proportions, taille=9.0, gras_derniere=False):
        total = sum(proportions)
        largeurs = [self.largeur * p / total for p in proportions]
        pad = 5

        def hauteur_ligne(cellules, gras):
            hs = [self._layout(str(c), taille, gras, largeur=w - 2 * pad).get_pixel_size()[1]
                  for c, w in zip(cellules, largeurs)]
            return max(hs) + 2 * pad

        def dessiner_ligne(cellules, gras, fond=None):
            h = hauteur_ligne(cellules, gras)
            if fond:
                self.cr.set_source_rgb(*fond)
                self.cr.rectangle(MARGE, self.y, self.largeur, h)
                self.cr.fill()
            x = MARGE
            for c, w in zip(cellules, largeurs):
                lay = self._layout(str(c), taille, gras, largeur=w - 2 * pad)
                self._dessiner(lay, x + pad, self.y + pad)
                x += w
            self.cr.set_source_rgb(*GRIS_CLAIR)
            self.cr.set_line_width(0.6)
            self.cr.move_to(MARGE, self.y + h)
            self.cr.line_to(MARGE + self.largeur, self.y + h)
            self.cr.stroke()
            self.y += h

        h_entete = hauteur_ligne(entetes, True)
        self.place(h_entete + (hauteur_ligne(lignes[0], False) if lignes else 0))
        dessiner_ligne(entetes, True, FOND_ENTETE)
        for i, ligne in enumerate(lignes):
            gras = gras_derniere and i == len(lignes) - 1
            h = hauteur_ligne(ligne, gras)
            if self.y + h > self.bas:
                self.nouvelle_page()
                dessiner_ligne(entetes, True, FOND_ENTETE)
            dessiner_ligne(ligne, gras)
        self.y += 10

    def terminer(self):
        self._pied()
        self.surface.finish()


def _date_du_jour():
    return _dt.date.today().strftime("%d/%m/%Y")


# --------------------------------------------------------- récapitulatif classe

def recap_classe_pdf(base, classe_id, periode, chemin):
    c = base.classe(classe_id)
    annee = base.annee(c["annee_id"])
    eleves = base.eleves(classe_id)
    matieres = base.matieres(classe_id)
    etats = base.etats_classe(classe_id, periode)
    moyennes = base.moyennes_classe(classe_id)
    per = libelle_periode(c["decoupage"], periode, long=True)
    termines = sum(1 for e in etats.values() if e == "termine")
    doc = Pdf(chemin, f"{c['nom']} — {per}")
    doc.entete(f"Conseil de classe — {c['nom']}",
               f"{per} · année {annee['libelle']} · {len(eleves)} élèves · "
               f"{termines} bilans terminés · édité le {_date_du_jour()}")
    for e in eleves:
        moys = moyennes.get(e["id"], {})
        cumul = base.moyenne_cumulee(moys, periode)
        b = base.bilan(e["id"], periode)
        appr = base.appreciations_eleve(e["id"])
        doc.place(70)
        doc.deux_colonnes(nom_complet(e),
                          f"Moyenne : {format_nombre(moys.get(periode))} · cumul : {format_nombre(cumul)}",
                          taille=11.5, gras=True)
        if b and b["decision"] and b["decision"] != "Aucune":
            note = f" — {b['decision_note']}" if b["decision_note"] else ""
            doc.texte(f"Décision du conseil : {b['decision']}{note}", 9.5, gras=True, couleur=BLEU)
        doc.texte("Bilan général", 9, gras=True, couleur=GRIS, apres=1)
        doc.texte((b["texte"] if b and b["texte"].strip() else "—"), 10, apres=8)
        lignes = []
        for m in matieres:
            a = appr.get((m["id"], periode))
            lignes.append([m["nom"], a["texte"] if a and a["texte"].strip() else "—"])
        if lignes:
            doc.tableau(["Matière", "Appréciation"], lignes, [1, 3.4], taille=9)
        doc.filet(apres=12)
    doc.terminer()
    return Path(chemin)


def recap_classe_ods(base, classe_id, chemin):
    c = base.classe(classe_id)
    eleves = base.eleves(classe_id)
    matieres = base.matieres(classe_id)
    moyennes = base.moyennes_classe(classe_id)
    feuilles = []
    for p in range(1, nb_periodes(c["decoupage"]) + 1):
        entete = ["Élève", "Moyenne", "Cumul annuel", *[m["nom"] for m in matieres],
                  "Bilan général", "Décision", "Remarque du conseil"]
        lignes = [entete]
        for e in eleves:
            moys = moyennes.get(e["id"], {})
            cumul = base.moyenne_cumulee(moys, p)
            appr = base.appreciations_eleve(e["id"])
            b = base.bilan(e["id"], p)
            lignes.append([
                nom_complet(e),
                moys.get(p),
                round(cumul, 2) if cumul is not None else None,
                *[(appr.get((m["id"], p))["texte"] if appr.get((m["id"], p)) else "") for m in matieres],
                b["texte"] if b else "",
                (b["decision"] if b and b["decision"] and b["decision"] != "Aucune" else ""),
                b["decision_note"] if b else "",
            ])
        feuilles.append((libelle_periode(c["decoupage"], p, long=True), lignes))
    largeurs = [5, 2.2, 2.6] + [8] * len(matieres) + [10, 4.5, 6]
    tableur.ecrire_ods(chemin, feuilles, largeurs)
    return Path(chemin)


# --------------------------------------------------------- répartition des suivis

def bilan_suivis(base, annee_id, enseignant_id):
    """Données du bilan d'un collègue : [(classe, heures, total, nb_eleves, Fraction)], total."""
    lignes = []
    total = 0
    for c in base.classes_pfmp(annee_id):
        heures = base.heures_classe(c["id"])
        if enseignant_id not in heures:
            continue
        nb = len(base.eleves(c["id"]))
        parts = calculs.repartir(heures, nb)
        q = parts.get(enseignant_id, 0)
        lignes.append((c, heures[enseignant_id], sum(heures.values()), nb, q))
        total += q
    return lignes, total


def bilan_suivis_pdf(base, annee_id, enseignant_id, chemin):
    ens = next(e for e in base.enseignants(annee_id) if e["id"] == enseignant_id)
    annee = base.annee(annee_id)
    lignes, total = bilan_suivis(base, annee_id, enseignant_id)
    doc = Pdf(chemin, f"Suivis PFMP — {ens['nom']}")
    doc.entete(f"Suivis PFMP — {ens['nom']}",
               f"Année {annee['libelle']} · répartition au prorata des heures · édité le {_date_du_jour()}")
    tab = [[c["nom"], calculs.format_heures(h), calculs.format_heures(t), str(n), calculs.format_quota(q)]
           for c, h, t, n, q in lignes]
    tab.append(["Total", "", "", "", calculs.format_quota(total)])
    doc.tableau(["Classe", "Vos heures", "Heures de l'équipe", "Élèves", "Élèves à suivre"],
                tab, [1.6, 1, 1.3, 0.8, 1.5], taille=9.5, gras_derniere=True)
    doc.texte("Calcul : élèves à suivre = (vos heures ÷ total des heures de l'équipe dans la classe) "
              "× nombre d'élèves de la classe. Résultat exact, sans arrondi ; la valeur décimale est "
              "donnée à 0,1 près.", 8.5, italique=True, couleur=GRIS, apres=14)
    for p in base.pfmps(annee_id):
        suivis = base.suivis(enseignant_id, p["id"])
        dates = f" (du {p['debut']} au {p['fin']})" if p["debut"] and p["fin"] else ""
        doc.texte(f"PFMP {p['numero']}{dates} — {len(suivis)} élève(s) attribué(s)", 11.5, gras=True,
                  apres=6)
        if not suivis:
            doc.texte("Aucun élève attribué pour l'instant.", 9.5, couleur=GRIS, apres=12)
            continue
        tab = []
        for s in suivis:
            entreprise = "\n".join(x for x in (s["entreprise"], s["adresse"]) if x) or "—"
            tab.append([f"{s['nom']} {s['prenom']}\n{s['classe_nom']}", entreprise,
                        (s["telephone"] or "—").replace(" ", "\u00a0"), s["tuteur"] or "—", s["visite_le"] or ""])
        doc.tableau(["Élève", "Entreprise", "Téléphone", "Tuteur", "Visite"], tab,
                    [1.3, 2.2, 1.3, 1.1, 0.8], taille=8.5)
    doc.terminer()
    return Path(chemin)


def etat_pfmp_texte(stage) -> str:
    return f"{RECHERCHE[stage['recherche']]} · {CONVENTION[stage['convention']]}"


def _visites_donnees(base, annee_id, numero):
    pfmp = next((p for p in base.pfmps(annee_id) if p["numero"] == numero), None)
    if pfmp is None:
        raise ValueError(f"PFMP {numero} introuvable pour cette année")
    return pfmp, base.stages(annee_id, pfmp["id"])


def _par_prof(stages):
    """[(nom du prof ou None, [stages])] : profs par ordre alphabétique, puis les élèves sans référent."""
    groupes: dict = {}
    for s in stages:
        groupes.setdefault(s["enseignant_nom"] or None, []).append(s)
    noms = sorted((n for n in groupes if n), key=normaliser)
    return [(n, groupes[n]) for n in noms] + ([(None, groupes[None])] if None in groupes else [])


def visites_pdf(base, annee_id, numero, chemin):
    """PDF des visites PFMP, une section par professeur référent : élèves, lieux de
    stage, téléphones, tuteurs, distances depuis l'établissement et dates de visite."""
    from . import geo
    annee = base.annee(annee_id)
    pfmp, stages = _visites_donnees(base, annee_id, numero)
    dates = (f"du {pfmp['debut']} au {pfmp['fin']}"
             if pfmp["debut"] and pfmp["fin"] else "dates non renseignées")
    doc = Pdf(chemin, f"Visites PFMP {numero} — {annee['libelle']}")
    doc.entete(f"Visites PFMP {numero}",
               f"Année {annee['libelle']} · {dates} · {len(stages)} élève(s) · "
               f"édité le {_date_du_jour()}")
    if not stages:
        doc.texte("Aucun élève pour cette PFMP.", 10, couleur=GRIS)
        doc.terminer()
        return Path(chemin)
    depart = geo.etablissement(base)
    avec_distances = any(geo.distance_km(base, s["adresse"]) is not None for s in stages)
    for prof, liste in _par_prof(stages):
        kms = [geo.distance_km(base, s["adresse"]) for s in liste]
        connus = [k for k in kms if k is not None]
        resume = f"{len(liste)} élève(s)"
        if connus:
            resume += f" · {geo.format_km(min(connus))[:-3]} à {geo.format_km(max(connus))}"
        doc.place(80)
        doc.deux_colonnes(prof or "Sans professeur référent", resume, taille=12, gras=True)
        tab = []
        for s in sorted(liste, key=lambda x: (normaliser(x["nom"]), normaliser(x["prenom"]))):
            km = geo.distance_km(base, s["adresse"])
            lieu = "\n".join(x for x in (s["entreprise"], s["adresse"]) if x) or "—"
            ligne = [f"{s['nom']} {s['prenom']}\n{s['classe_nom']}", lieu,
                     (s["telephone"] or "—").replace(" ", "\u00a0"), s["tuteur"] or "—"]
            if avec_distances:
                ligne.append(geo.format_km(km)[:-3] if km is not None else "—")
            ligne.append(s["visite_le"] or "")
            tab.append(ligne)
        entetes = ["Élève", "Lieu de stage", "Tél.", "Tuteur"]
        proportions = [1.35, 2.35, 1.2, 1.2]
        if avec_distances:
            entetes.append("Km")
            proportions.append(0.55)
        entetes.append("Visite")
        proportions.append(0.85)
        doc.tableau(entetes, tab, proportions, taille=8.5)
        doc.espace(6)
    note = "Lieux de stage, contacts des tuteurs et professeurs référents — document généré par Livret."
    if avec_distances:
        note += f" Km : distance à vol d'oiseau depuis {depart}."
    doc.texte(note, 8.5, italique=True, couleur=GRIS, apres=14)
    doc.terminer()
    return Path(chemin)


def visites_xlsx(base, annee_id, numero, chemin):
    """Classeur des visites PFMP : élèves, lieux, tuteurs, profs référents."""
    _pfmp, stages = _visites_donnees(base, annee_id, numero)
    from . import geo
    table = [["Prof référent", "Élève", "Classe", "Entreprise", "Adresse", "Téléphone", "Tuteur",
              "Distance (km, à vol d'oiseau)", "Recherche", "Convention", "Visite"]]
    for prof, liste in _par_prof(stages):
        for s in sorted(liste, key=lambda x: (normaliser(x["nom"]), normaliser(x["prenom"]))):
            conv = CONVENTION[s["convention"]] if s["convention"] is not None else ""
            km = geo.distance_km(base, s["adresse"])
            table.append([prof or "", f"{s['nom']} {s['prenom']}", s["classe_nom"], s["entreprise"],
                          s["adresse"], s["telephone"], s["tuteur"],
                          round(km, 1) if km is not None else "",
                          RECHERCHE.get(s["recherche"], s["recherche"]), conv, s["visite_le"]])
    tableur.ecrire_xlsx(chemin, [(f"Visites PFMP {numero}", table)],
                        [3, 3, 2, 4, 5, 3, 3, 2.5, 2.5, 3, 2])
    return Path(chemin)
