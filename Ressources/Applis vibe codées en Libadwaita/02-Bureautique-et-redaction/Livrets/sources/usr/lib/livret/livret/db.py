"""Base de données SQLite de Livret.

Toutes les données restent sur la machine, dans ~/.local/share/livret/
(ou $XDG_DATA_HOME/livret). Chaque modification est écrite immédiatement.
Ce module ne dépend pas de GTK : il est testable hors session graphique.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sqlite3
import unicodedata
from pathlib import Path

SCHEMA_VERSION = 3
FORMAT_JSON = "livret"
# Les exports JSON faits avant le renommage portent « bulletin » : on continue
# de les accepter, sinon les sauvegardes déjà enregistrées deviennent illisibles.
FORMATS_ACCEPTES = ("livret", "bulletin")
NB_SAUVEGARDES = 10

DECOUPAGES = {"T": 3, "S": 2}
DECISIONS = [
    "Aucune",
    "Félicitations",
    "Compliments",
    "Encouragements",
    "Avertissement travail",
    "Avertissement comportement",
    "Avertissement assiduité",
]
RECHERCHE = {"en_cours": "En cours", "terminee": "Terminée"}
CONVENTION = [
    "Signature profs",
    "Signature parents",
    "Signature direction",
    "Finalisée",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    cle    TEXT PRIMARY KEY,
    valeur TEXT
);
CREATE TABLE IF NOT EXISTS annee (
    id          INTEGER PRIMARY KEY,
    libelle     TEXT NOT NULL UNIQUE,
    archivee    INTEGER NOT NULL DEFAULT 0,
    archivee_le TEXT
);
CREATE TABLE IF NOT EXISTS classe (
    id             INTEGER PRIMARY KEY,
    annee_id       INTEGER NOT NULL REFERENCES annee(id) ON DELETE CASCADE,
    nom            TEXT NOT NULL,
    decoupage      TEXT NOT NULL DEFAULT 'T' CHECK (decoupage IN ('T', 'S')),
    limite_matiere INTEGER NOT NULL DEFAULT 400,
    limite_bilan   INTEGER NOT NULL DEFAULT 600,
    pfmp           INTEGER NOT NULL DEFAULT 1,
    UNIQUE (annee_id, nom)
);
CREATE TABLE IF NOT EXISTS eleve (
    id        INTEGER PRIMARY KEY,
    classe_id INTEGER NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    nom       TEXT NOT NULL,
    prenom    TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS matiere (
    id        INTEGER PRIMARY KEY,
    classe_id INTEGER NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    nom       TEXT NOT NULL,
    ordre     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS appreciation (
    eleve_id   INTEGER NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    matiere_id INTEGER NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    periode    INTEGER NOT NULL,
    texte      TEXT NOT NULL DEFAULT '',
    termine    INTEGER NOT NULL DEFAULT 0,
    moyenne    REAL,
    modifie_le TEXT,
    PRIMARY KEY (eleve_id, matiere_id, periode)
);
CREATE TABLE IF NOT EXISTS bilan (
    eleve_id      INTEGER NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    periode       INTEGER NOT NULL,
    texte         TEXT NOT NULL DEFAULT '',
    termine       INTEGER NOT NULL DEFAULT 0,
    moyenne       REAL,
    decision      TEXT,
    decision_note TEXT NOT NULL DEFAULT '',
    modifie_le    TEXT,
    PRIMARY KEY (eleve_id, periode)
);
CREATE TABLE IF NOT EXISTS phrase (
    id        INTEGER PRIMARY KEY,
    categorie TEXT NOT NULL DEFAULT '',
    texte     TEXT NOT NULL,
    mots_cles TEXT NOT NULL DEFAULT '',
    ordre     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pfmp (
    id       INTEGER PRIMARY KEY,
    annee_id INTEGER NOT NULL REFERENCES annee(id) ON DELETE CASCADE,
    numero   INTEGER NOT NULL CHECK (numero IN (1, 2)),
    debut    TEXT NOT NULL DEFAULT '',
    fin      TEXT NOT NULL DEFAULT '',
    UNIQUE (annee_id, numero)
);
CREATE TABLE IF NOT EXISTS enseignant (
    id       INTEGER PRIMARY KEY,
    annee_id INTEGER NOT NULL REFERENCES annee(id) ON DELETE CASCADE,
    nom      TEXT NOT NULL,
    UNIQUE (annee_id, nom)
);
CREATE TABLE IF NOT EXISTS repartition (
    enseignant_id INTEGER NOT NULL REFERENCES enseignant(id) ON DELETE CASCADE,
    classe_id     INTEGER NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    heures        REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (enseignant_id, classe_id)
);
CREATE TABLE IF NOT EXISTS entreprise (
    id        INTEGER PRIMARY KEY,
    nom       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    adresse   TEXT NOT NULL DEFAULT '',
    telephone TEXT NOT NULL DEFAULT '',
    tuteur    TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS stage (
    eleve_id      INTEGER NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    pfmp_id       INTEGER NOT NULL REFERENCES pfmp(id) ON DELETE CASCADE,
    recherche     TEXT NOT NULL DEFAULT 'en_cours'
                  CHECK (recherche IN ('en_cours', 'terminee')),
    convention    INTEGER NOT NULL DEFAULT 0 CHECK (convention BETWEEN 0 AND 3),
    enseignant_id INTEGER REFERENCES enseignant(id) ON DELETE SET NULL,
    entreprise    TEXT NOT NULL DEFAULT '',
    adresse       TEXT NOT NULL DEFAULT '',
    telephone     TEXT NOT NULL DEFAULT '',
    tuteur        TEXT NOT NULL DEFAULT '',
    visite_le     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (eleve_id, pfmp_id)
);
CREATE TABLE IF NOT EXISTS geocache (
    adresse TEXT PRIMARY KEY,   -- adresse normalisée
    lat     REAL,
    lon     REAL,               -- NULL/NULL : adresse introuvable
    maj_le  TEXT
);
CREATE INDEX IF NOT EXISTS i_classe_annee ON classe(annee_id);
CREATE INDEX IF NOT EXISTS i_eleve_classe ON eleve(classe_id);
CREATE INDEX IF NOT EXISTS i_matiere_classe ON matiere(classe_id);
CREATE INDEX IF NOT EXISTS i_stage_ens ON stage(enseignant_id);
"""

# Ordre d'insertion compatible avec les clés étrangères.
TABLES = [
    "meta", "annee", "classe", "eleve", "matiere", "appreciation", "bilan",
    "phrase", "pfmp", "enseignant", "repartition", "entreprise", "stage",
]

PHRASES_INITIALES = [
    ("Bilan", "Très bon trimestre : continuez ainsi !", "félicitations excellent bravo"),
    ("Bilan", "Ensemble satisfaisant. Poursuivez vos efforts.", "satisfaisant correct"),
    ("Bilan", "Des progrès encourageants, qu'il faut maintenant confirmer.", "progrès encourageant"),
    ("Bilan", "Trimestre insuffisant : un sursaut est indispensable.", "insuffisant sursaut alerte"),
    ("Travail", "Travail sérieux et régulier.", "sérieux régulier investissement"),
    ("Travail", "Le travail personnel doit devenir plus régulier.", "irrégulier travail maison leçons"),
    ("Travail", "Participation active et pertinente en classe.", "participation oral"),
    ("Travail", "Les bases sont acquises ; il reste à approfondir.", "bases approfondir"),
    ("Travail", "Il faut apprendre les leçons avec davantage de rigueur.", "leçons rigueur apprendre"),
    ("Comportement", "Attitude positive et respectueuse.", "attitude respect comportement"),
    ("Comportement", "Le bavardage nuit à votre concentration et à celle de la classe.", "bavardage concentration"),
    ("Assiduité", "Les absences répétées pénalisent vos apprentissages.", "absences assiduité"),
    ("Assiduité", "Les retards doivent cesser.", "retards ponctualité assiduité"),
    ("Professionnel", "Bonne implication lors de la période en entreprise.", "pfmp stage entreprise"),
    ("Professionnel", "La recherche de stage doit être plus active.", "pfmp stage recherche"),
    ("Orientation", "Le projet d'orientation se précise : continuez à vous renseigner.", "orientation projet"),
]


# --------------------------------------------------------------------- outils

def dossier_donnees() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share")
    dossier = Path(base) / "livret"
    ancien = Path(base) / "bulletin"
    # Renommage de l'appli : on récupère le dossier de données existant au lieu
    # d'en créer un vide, sinon classes, appréciations et PFMP disparaissent.
    if not dossier.exists() and ancien.is_dir():
        try:
            ancien.rename(dossier)
        except OSError:
            dossier = ancien  # repli : on continue avec l'ancien dossier
    dossier.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(dossier, 0o700)  # données d'élèves : accès réservé à l'utilisateur
    except OSError:
        pass
    return dossier


def _chemin_base() -> Path:
    """Chemin de la base, en récupérant le fichier de l'ancien nom si besoin."""
    dossier = dossier_donnees()
    chemin = dossier / "livret.db"
    ancien = dossier / "bulletin.db"
    # Le renommage a déplacé le dossier de données ; la base porte encore
    # l'ancien nom. Sans ce rattrapage, l'appli créerait une base vide et les
    # classes déjà saisies sembleraient disparues.
    if not chemin.exists() and ancien.exists():
        try:
            ancien.rename(chemin)
            # Les journaux WAL accompagnent la base : sans eux, les dernières
            # modifications non encore fusionnées seraient perdues.
            for suffixe in ("-wal", "-shm"):
                cote = Path(f"{ancien}{suffixe}")
                if cote.exists():
                    cote.rename(Path(f"{chemin}{suffixe}"))
        except OSError:
            return ancien  # repli : on continue avec l'ancien fichier
    return chemin


def maintenant() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def annee_scolaire_courante(aujourdhui: _dt.date | None = None) -> str:
    d = aujourdhui or _dt.date.today()
    debut = d.year if d.month >= 8 else d.year - 1
    return f"{debut}-{debut + 1}"


def normaliser(texte: str) -> str:
    """Minuscules sans accents, pour les recherches et les comparaisons."""
    nfkd = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).casefold().strip()


def cle_eleve(nom: str, prenom: str) -> str:
    return " ".join((normaliser(nom) + " " + normaliser(prenom)).replace("-", " ").split())


def nb_periodes(decoupage: str) -> int:
    return DECOUPAGES.get(decoupage, 3)


def libelle_periode(decoupage: str, periode: int, long: bool = False) -> str:
    if decoupage == "S":
        if long:
            return "1er semestre" if periode == 1 else f"{periode}e semestre"
        return f"S{periode}"
    if long:
        return "1er trimestre" if periode == 1 else f"{periode}e trimestre"
    return f"T{periode}"


def nom_complet(eleve) -> str:
    return f"{eleve['nom']} {eleve['prenom']}".strip()


def format_nombre(valeur, decimales: int = 1) -> str:
    if valeur is None:
        return "—"
    return f"{valeur:.{decimales}f}".replace(".", ",")


def etat_texte(texte: str | None, termine) -> str:
    if not texte or not texte.strip():
        return "vide"
    return "termine" if termine else "brouillon"


# ----------------------------------------------------------------------- base

class Base:
    def __init__(self, chemin: str | os.PathLike | None = None):
        self.chemin = Path(chemin) if chemin else _chemin_base()
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        neuve = not self.chemin.exists()
        self.cx = sqlite3.connect(self.chemin)
        self.cx.row_factory = sqlite3.Row
        self.cx.execute("PRAGMA foreign_keys = ON")
        self.cx.execute("PRAGMA journal_mode = WAL")
        self.cx.execute("PRAGMA synchronous = NORMAL")
        self.cx.executescript(SCHEMA)
        try:
            os.chmod(self.chemin, 0o600)
        except OSError:
            pass
        if neuve:
            self._amorcer()
        self._migrer()
        self.annee_active()  # garantit qu'au moins une année existe

    def _migrer(self):
        """Ajoute les colonnes apparues dans les versions récentes."""
        colonnes = {r[1] for r in self.cx.execute("PRAGMA table_info(appreciation)")}
        if "moyenne" not in colonnes:
            with self.cx:
                self.cx.execute("ALTER TABLE appreciation ADD COLUMN moyenne REAL")
        colonnes = {r[1] for r in self.cx.execute("PRAGMA table_info(classe)")}
        if "pfmp" not in colonnes:
            # Suivi PFMP par classe. Pour une base existante, on ne garde en PFMP que les
            # classes qui ont déjà des stages saisis (s'il n'y en a aucune : toutes).
            with self.cx:
                self.cx.execute("ALTER TABLE classe ADD COLUMN pfmp INTEGER NOT NULL DEFAULT 1")
                avec_stages = {r[0] for r in self.cx.execute(
                    "SELECT DISTINCT e.classe_id FROM stage s JOIN eleve e ON e.id = s.eleve_id")}
                if avec_stages:
                    self.cx.execute(f"UPDATE classe SET pfmp = 0 WHERE id NOT IN "
                                    f"({','.join('?' * len(avec_stages))})", tuple(avec_stages))
        self.definir_reglage("version_schema", str(SCHEMA_VERSION))

    def _amorcer(self):
        with self.cx:
            self.cx.execute("INSERT OR REPLACE INTO meta VALUES ('version_schema', ?)",
                            (str(SCHEMA_VERSION),))
            for i, (cat, txt, mots) in enumerate(PHRASES_INITIALES):
                self.cx.execute(
                    "INSERT INTO phrase (categorie, texte, mots_cles, ordre) VALUES (?,?,?,?)",
                    (cat, txt, mots, i))

    def fermer(self):
        try:
            self.cx.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        self.cx.close()

    def _x(self, sql, params=()):
        with self.cx:
            return self.cx.execute(sql, params)

    def _un(self, sql, params=()):
        return self.cx.execute(sql, params).fetchone()

    def _tous(self, sql, params=()):
        return self.cx.execute(sql, params).fetchall()

    # ------------------------------------------------------------ sauvegardes
    def dossier_sauvegardes(self) -> Path:
        d = self.chemin.parent / "sauvegardes"
        d.mkdir(exist_ok=True)
        return d

    def sauvegarder(self, motif: str = "auto") -> Path:
        horodatage = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        cible = self.dossier_sauvegardes() / f"livret-{horodatage}-{motif}.db"
        n = 1
        while cible.exists():
            cible = self.dossier_sauvegardes() / f"livret-{horodatage}-{motif}-{n}.db"
            n += 1
        dest = sqlite3.connect(cible)
        with dest:
            self.cx.backup(dest)
        dest.close()
        try:
            os.chmod(cible, 0o600)
        except OSError:
            pass
        # On ratisse aussi les « bulletin-… » : les sauvegardes faites avant le
        # renommage doivent continuer d'être purgées.
        anciennes = sorted(s for p in ("livret", "bulletin")
                           for s in self.dossier_sauvegardes().glob(f"{p}-*-{motif}*.db"))
        for vieux in anciennes[:-NB_SAUVEGARDES]:
            vieux.unlink(missing_ok=True)
        return cible

    # --------------------------------------------------------------- réglages
    def reglage(self, cle, defaut=None):
        r = self._un("SELECT valeur FROM meta WHERE cle = ?", (cle,))
        return r["valeur"] if r else defaut

    def definir_reglage(self, cle, valeur):
        self._x("INSERT OR REPLACE INTO meta (cle, valeur) VALUES (?, ?)",
                (cle, None if valeur is None else str(valeur)))

    def reglage_bool(self, cle, defaut=False) -> bool:
        v = self.reglage(cle)
        return defaut if v is None else v == "1"

    # ----------------------------------------------------------------- années
    def annees(self):
        return self._tous("SELECT * FROM annee ORDER BY libelle DESC")

    def annee(self, annee_id):
        return self._un("SELECT * FROM annee WHERE id = ?", (annee_id,))

    def annee_active(self) -> int:
        v = self.reglage("annee_active")
        if v and self.annee(int(v)):
            return int(v)
        r = self._un("SELECT id FROM annee ORDER BY archivee, libelle DESC LIMIT 1")
        if r:
            aid = r["id"]
        else:
            aid = self._x("INSERT INTO annee (libelle) VALUES (?)",
                          (annee_scolaire_courante(),)).lastrowid
        self.definir_reglage("annee_active", aid)
        return aid

    def choisir_annee(self, annee_id):
        self.definir_reglage("annee_active", annee_id)

    def creer_annee(self, libelle: str, reprendre_de: int | None = None) -> int:
        libelle = libelle.strip()
        if not libelle:
            raise ValueError("Libellé d'année vide")
        if self._un("SELECT 1 FROM annee WHERE libelle = ?", (libelle,)):
            raise ValueError(f"L'année {libelle} existe déjà")
        with self.cx:
            aid = self.cx.execute("INSERT INTO annee (libelle) VALUES (?)", (libelle,)).lastrowid
            if reprendre_de:
                for c in self.classes(reprendre_de):
                    cid = self.cx.execute(
                        "INSERT INTO classe (annee_id, nom, decoupage, limite_matiere, limite_bilan, pfmp)"
                        " VALUES (?,?,?,?,?,?)",
                        (aid, c["nom"], c["decoupage"], c["limite_matiere"], c["limite_bilan"], c["pfmp"])
                    ).lastrowid
                    for m in self.matieres(c["id"]):
                        self.cx.execute(
                            "INSERT INTO matiere (classe_id, nom, ordre) VALUES (?,?,?)",
                            (cid, m["nom"], m["ordre"]))
                for e in self.enseignants(reprendre_de):
                    self.cx.execute("INSERT INTO enseignant (annee_id, nom) VALUES (?,?)",
                                    (aid, e["nom"]))
        self.choisir_annee(aid)
        return aid

    def archiver_annee(self, annee_id, archivee=True):
        self._x("UPDATE annee SET archivee = ?, archivee_le = ? WHERE id = ?",
                (1 if archivee else 0, maintenant() if archivee else None, annee_id))

    def annee_archivee(self, annee_id) -> bool:
        a = self.annee(annee_id)
        return bool(a and a["archivee"])

    # ---------------------------------------------------------------- classes
    def classes(self, annee_id):
        rows = self._tous("SELECT * FROM classe WHERE annee_id = ?", (annee_id,))
        return sorted(rows, key=lambda c: normaliser(c["nom"]))

    def classes_pfmp(self, annee_id):
        """Classes dont on suit les PFMP (réglage « Suivi des PFMP » de la classe)."""
        return [c for c in self.classes(annee_id) if c["pfmp"]]

    def classe(self, classe_id):
        return self._un("SELECT * FROM classe WHERE id = ?", (classe_id,))

    def creer_classe(self, annee_id, nom, decoupage="T", limite_matiere=None,
                     limite_bilan=None, matieres_de=None, pfmp=True) -> int:
        nom = nom.strip()
        if not nom:
            raise ValueError("Nom de classe vide")
        if self._un("SELECT 1 FROM classe WHERE annee_id = ? AND nom = ?", (annee_id, nom)):
            raise ValueError(f"La classe {nom} existe déjà")
        lm = int(limite_matiere or self.reglage("limite_matiere_defaut", 400))
        lb = int(limite_bilan or self.reglage("limite_bilan_defaut", 600))
        with self.cx:
            cid = self.cx.execute(
                "INSERT INTO classe (annee_id, nom, decoupage, limite_matiere, limite_bilan, pfmp)"
                " VALUES (?,?,?,?,?,?)", (annee_id, nom, decoupage, lm, lb, 1 if pfmp else 0)).lastrowid
            if matieres_de:
                for m in self.matieres(matieres_de):
                    self.cx.execute("INSERT INTO matiere (classe_id, nom, ordre) VALUES (?,?,?)",
                                    (cid, m["nom"], m["ordre"]))
        return cid

    def maj_classe(self, classe_id, **champs):
        autorises = {"nom", "decoupage", "limite_matiere", "limite_bilan", "pfmp"}
        champs = {k: v for k, v in champs.items() if k in autorises}
        if not champs:
            return
        if "nom" in champs:
            champs["nom"] = champs["nom"].strip()
            if not champs["nom"]:
                raise ValueError("Nom de classe vide")
        sets = ", ".join(f"{k} = ?" for k in champs)
        self._x(f"UPDATE classe SET {sets} WHERE id = ?", (*champs.values(), classe_id))

    def supprimer_classe(self, classe_id):
        self._x("DELETE FROM classe WHERE id = ?", (classe_id,))

    # ----------------------------------------------------------------- élèves
    def eleves(self, classe_id):
        rows = self._tous("SELECT * FROM eleve WHERE classe_id = ?", (classe_id,))
        return sorted(rows, key=lambda e: (normaliser(e["nom"]), normaliser(e["prenom"])))

    def eleve(self, eleve_id):
        return self._un("SELECT * FROM eleve WHERE id = ?", (eleve_id,))

    def eleves_annee(self, annee_id):
        rows = self._tous(
            "SELECT e.*, c.nom AS classe_nom FROM eleve e JOIN classe c ON c.id = e.classe_id"
            " WHERE c.annee_id = ?", (annee_id,))
        return sorted(rows, key=lambda e: (normaliser(e["classe_nom"]), normaliser(e["nom"]),
                                           normaliser(e["prenom"])))

    def ajouter_eleve(self, classe_id, nom, prenom="") -> int:
        nom, prenom = nom.strip(), prenom.strip()
        if not nom and not prenom:
            raise ValueError("Nom d'élève vide")
        return self._x("INSERT INTO eleve (classe_id, nom, prenom) VALUES (?,?,?)",
                       (classe_id, nom, prenom)).lastrowid

    def maj_eleve(self, eleve_id, nom, prenom):
        self._x("UPDATE eleve SET nom = ?, prenom = ? WHERE id = ?",
                (nom.strip(), prenom.strip(), eleve_id))

    def supprimer_eleve(self, eleve_id):
        self._x("DELETE FROM eleve WHERE id = ?", (eleve_id,))

    # --------------------------------------------------------------- matières
    def matieres(self, classe_id):
        return self._tous("SELECT * FROM matiere WHERE classe_id = ? ORDER BY ordre, id",
                          (classe_id,))

    def ajouter_matiere(self, classe_id, nom) -> int:
        nom = nom.strip()
        if not nom:
            raise ValueError("Nom de matière vide")
        r = self._un("SELECT COALESCE(MAX(ordre), -1) + 1 AS o FROM matiere WHERE classe_id = ?",
                     (classe_id,))
        return self._x("INSERT INTO matiere (classe_id, nom, ordre) VALUES (?,?,?)",
                       (classe_id, nom, r["o"])).lastrowid

    def renommer_matiere(self, matiere_id, nom):
        if nom.strip():
            self._x("UPDATE matiere SET nom = ? WHERE id = ?", (nom.strip(), matiere_id))

    def deplacer_matiere(self, matiere_id, delta: int):
        m = self._un("SELECT * FROM matiere WHERE id = ?", (matiere_id,))
        liste = [r["id"] for r in self.matieres(m["classe_id"])]
        i = liste.index(matiere_id)
        j = max(0, min(len(liste) - 1, i + delta))
        if i == j:
            return
        liste.insert(j, liste.pop(i))
        with self.cx:
            for ordre, mid in enumerate(liste):
                self.cx.execute("UPDATE matiere SET ordre = ? WHERE id = ?", (ordre, mid))

    def supprimer_matiere(self, matiere_id):
        self._x("DELETE FROM matiere WHERE id = ?", (matiere_id,))

    # ---------------------------------------------------------- appréciations
    def appreciation(self, eleve_id, matiere_id, periode):
        return self._un("SELECT * FROM appreciation WHERE eleve_id = ? AND matiere_id = ?"
                        " AND periode = ?", (eleve_id, matiere_id, periode))

    def appreciations_eleve(self, eleve_id) -> dict:
        rows = self._tous("SELECT * FROM appreciation WHERE eleve_id = ?", (eleve_id,))
        return {(r["matiere_id"], r["periode"]): r for r in rows}

    def enregistrer_appreciation(self, eleve_id, matiere_id, periode, texte=None, termine=None,
                                 moyenne=None):
        with self.cx:
            self.cx.execute("INSERT OR IGNORE INTO appreciation (eleve_id, matiere_id, periode)"
                            " VALUES (?,?,?)", (eleve_id, matiere_id, periode))
            if texte is not None:
                self.cx.execute("UPDATE appreciation SET texte = ?, modifie_le = ? WHERE eleve_id = ?"
                                " AND matiere_id = ? AND periode = ?",
                                (texte, maintenant(), eleve_id, matiere_id, periode))
            if termine is not None:
                self.cx.execute("UPDATE appreciation SET termine = ? WHERE eleve_id = ?"
                                " AND matiere_id = ? AND periode = ?",
                                (1 if termine else 0, eleve_id, matiere_id, periode))
            if moyenne is not None:
                self.cx.execute("UPDATE appreciation SET moyenne = ? WHERE eleve_id = ?"
                                " AND matiere_id = ? AND periode = ?",
                                (float(moyenne), eleve_id, matiere_id, periode))

    def moyenne_matiere(self, eleve_id, periode):
        """Moyenne des notes de matières disponibles (import des collègues), sinon None."""
        r = self._un("SELECT AVG(moyenne) AS m, COUNT(moyenne) AS n FROM appreciation"
                     " WHERE eleve_id = ? AND periode = ? AND moyenne IS NOT NULL",
                     (eleve_id, periode))
        return r["m"] if r and r["n"] else None

    def notes_matiere(self, eleve_id, periode) -> dict:
        """{matiere_id: moyenne} pour la période."""
        return {r["matiere_id"]: r["moyenne"] for r in
                self._tous("SELECT matiere_id, moyenne FROM appreciation WHERE eleve_id = ?"
                           " AND periode = ? AND moyenne IS NOT NULL", (eleve_id, periode))}

    def assurer_matiere(self, classe_id, nom) -> int:
        """Identifiant de la matière, créée si elle n'existe pas encore."""
        nom = " ".join((nom or "").split())
        if not nom:
            raise ValueError("Nom de matière vide")
        cible = normaliser(nom)
        for m in self.matieres(classe_id):
            if normaliser(m["nom"]) == cible:
                return m["id"]
        return self.ajouter_matiere(classe_id, nom)

    def bilan(self, eleve_id, periode):
        return self._un("SELECT * FROM bilan WHERE eleve_id = ? AND periode = ?",
                        (eleve_id, periode))

    def bilans_eleve(self, eleve_id) -> dict:
        return {r["periode"]: r for r in
                self._tous("SELECT * FROM bilan WHERE eleve_id = ?", (eleve_id,))}

    _CHAMPS_BILAN = {"texte", "termine", "moyenne", "decision", "decision_note"}

    def enregistrer_bilan(self, eleve_id, periode, **champs):
        champs = {k: v for k, v in champs.items() if k in self._CHAMPS_BILAN}
        if "termine" in champs:
            champs["termine"] = 1 if champs["termine"] else 0
        with self.cx:
            self.cx.execute("INSERT OR IGNORE INTO bilan (eleve_id, periode) VALUES (?,?)",
                            (eleve_id, periode))
            if champs:
                if "texte" in champs:
                    champs["modifie_le"] = maintenant()
                sets = ", ".join(f"{k} = ?" for k in champs)
                self.cx.execute(f"UPDATE bilan SET {sets} WHERE eleve_id = ? AND periode = ?",
                                (*champs.values(), eleve_id, periode))

    def moyennes_classe(self, classe_id) -> dict:
        """{eleve_id: {periode: moyenne}}"""
        res: dict = {}
        for r in self._tous("SELECT b.eleve_id, b.periode, b.moyenne FROM bilan b"
                            " JOIN eleve e ON e.id = b.eleve_id"
                            " WHERE e.classe_id = ? AND b.moyenne IS NOT NULL", (classe_id,)):
            res.setdefault(r["eleve_id"], {})[r["periode"]] = r["moyenne"]
        return res

    @staticmethod
    def moyenne_cumulee(moyennes: dict, jusqua: int):
        """Moyenne des moyennes de période disponibles, de la période 1 à `jusqua`."""
        vals = [v for p, v in moyennes.items() if p <= jusqua and v is not None]
        return sum(vals) / len(vals) if vals else None

    def etat_eleve(self, eleve_id, periode, matiere_ids) -> str:
        return self.etats_classe_pour([eleve_id], periode, matiere_ids)[eleve_id]

    def etats_classe(self, classe_id, periode) -> dict:
        ids = [e["id"] for e in self.eleves(classe_id)]
        mids = [m["id"] for m in self.matieres(classe_id)]
        return self.etats_classe_pour(ids, periode, mids)

    def etats_classe_pour(self, eleve_ids, periode, matiere_ids) -> dict:
        """vide : rien d'écrit ; terminé : bilan et toutes les matières terminés ;
        brouillon : le reste."""
        if not eleve_ids:
            return {}
        marques = ",".join("?" * len(eleve_ids))
        appr: dict = {}
        for r in self._tous(f"SELECT * FROM appreciation WHERE periode = ? AND eleve_id IN ({marques})",
                            (periode, *eleve_ids)):
            appr.setdefault(r["eleve_id"], {})[r["matiere_id"]] = etat_texte(r["texte"], r["termine"])
        bil = {r["eleve_id"]: etat_texte(r["texte"], r["termine"]) for r in
               self._tous(f"SELECT * FROM bilan WHERE periode = ? AND eleve_id IN ({marques})",
                          (periode, *eleve_ids))}
        res = {}
        for eid in eleve_ids:
            etats = [appr.get(eid, {}).get(mid, "vide") for mid in matiere_ids]
            etats.append(bil.get(eid, "vide"))
            if all(e == "vide" for e in etats):
                res[eid] = "vide"
            elif all(e == "termine" for e in etats):
                res[eid] = "termine"
            else:
                res[eid] = "brouillon"
        return res

    def importer_eleves(self, classe_id, lignes, periode=None, ajouter_absents=True) -> dict:
        """lignes : [(nom, prenom, moyenne|None)]. Rapproche par nom et prénom
        (sans accents ni casse), ajoute les absents si demandé, met à jour les moyennes."""
        existants = {cle_eleve(e["nom"], e["prenom"]): e["id"] for e in self.eleves(classe_id)}
        bilan = {"ajoutes": 0, "moyennes": 0, "ignores": []}
        for nom, prenom, moyenne in lignes:
            cle = cle_eleve(nom, prenom)
            if not cle:
                continue
            eid = existants.get(cle)
            if eid is None:
                if not ajouter_absents:
                    bilan["ignores"].append(f"{nom} {prenom}".strip())
                    continue
                eid = self.ajouter_eleve(classe_id, nom, prenom)
                existants[cle] = eid
                bilan["ajoutes"] += 1
            if periode and moyenne is not None:
                self.enregistrer_bilan(eid, periode, moyenne=float(moyenne))
                bilan["moyennes"] += 1
        return bilan

    def importer_commentaires(self, classe_id, periode, enregistrements, ajouter_absents=True,
                              creer_matieres=True, calculer_moyennes=True) -> dict:
        """Importe les appréciations et les moyennes par discipline des collègues.

        enregistrements : [(nom, prenom, discipline, moyenne|None, commentaire)].
        Crée les disciplines manquantes, écrit le commentaire comme appréciation de la
        période (marquée terminée) et enregistre la moyenne de la discipline. Si un élève
        n'a pas encore de moyenne générale pour cette période, elle est calculée comme la
        moyenne de ses notes de disciplines.
        """
        existants = {cle_eleve(e["nom"], e["prenom"]): e["id"] for e in self.eleves(classe_id)}
        matieres_avant = {m["id"] for m in self.matieres(classe_id)}
        bilan = {"eleves": 0, "ajoutes": 0, "disciplines": 0, "commentaires": 0,
                 "notes": 0, "moyennes_generales": 0, "ignores": []}
        touches: set[int] = set()
        for nom, prenom, discipline, moyenne, commentaire in enregistrements:
            discipline = " ".join((discipline or "").split())
            commentaire = (commentaire or "").strip()
            cle = cle_eleve(nom, prenom)
            if not cle or not discipline or (moyenne is None and not commentaire):
                continue
            eid = existants.get(cle)
            if eid is None:
                if not ajouter_absents:
                    bilan["ignores"].append(f"{nom} {prenom}".strip())
                    continue
                eid = self.ajouter_eleve(classe_id, nom, prenom)
                existants[cle] = eid
                bilan["ajoutes"] += 1
            if creer_matieres:
                mid = self.assurer_matiere(classe_id, discipline)
            else:
                mid = next((m["id"] for m in self.matieres(classe_id)
                            if normaliser(m["nom"]) == normaliser(discipline)), None)
            if mid is None:
                bilan["ignores"].append(discipline)
                continue
            self.enregistrer_appreciation(eid, mid, periode,
                                          texte=commentaire or None,
                                          termine=True if commentaire else None,
                                          moyenne=moyenne)
            if commentaire:
                bilan["commentaires"] += 1
            if moyenne is not None:
                bilan["notes"] += 1
            touches.add(eid)
        bilan["disciplines"] = len({m["id"] for m in self.matieres(classe_id)}) - len(matieres_avant)
        if calculer_moyennes:
            for eid in touches:
                b = self.bilan(eid, periode)
                if b is not None and b["moyenne"] is not None:
                    continue
                moy = self.moyenne_matiere(eid, periode)
                if moy is not None:
                    self.enregistrer_bilan(eid, periode, moyenne=moy)
                    bilan["moyennes_generales"] += 1
        bilan["eleves"] = len(touches)
        return bilan

    # ---------------------------------------------------------------- phrases
    def phrases(self, recherche: str = ""):
        rows = self._tous("SELECT * FROM phrase ORDER BY categorie COLLATE NOCASE, ordre, id")
        mots = normaliser(recherche).split()
        if not mots:
            return list(rows)
        res = []
        for r in rows:
            foin = normaliser(f"{r['texte']} {r['mots_cles']} {r['categorie']}")
            if all(m in foin for m in mots):
                res.append(r)
        return res

    def categories_phrases(self):
        return [r["categorie"] for r in
                self._tous("SELECT DISTINCT categorie FROM phrase ORDER BY categorie COLLATE NOCASE")]

    def ajouter_phrase(self, categorie, texte, mots_cles="") -> int:
        if not texte.strip():
            raise ValueError("Phrase vide")
        r = self._un("SELECT COALESCE(MAX(ordre), -1) + 1 AS o FROM phrase")
        return self._x("INSERT INTO phrase (categorie, texte, mots_cles, ordre) VALUES (?,?,?,?)",
                       (categorie.strip(), texte.strip(), mots_cles.strip(), r["o"])).lastrowid

    def maj_phrase(self, phrase_id, categorie, texte, mots_cles):
        self._x("UPDATE phrase SET categorie = ?, texte = ?, mots_cles = ? WHERE id = ?",
                (categorie.strip(), texte.strip(), mots_cles.strip(), phrase_id))

    def supprimer_phrase(self, phrase_id):
        self._x("DELETE FROM phrase WHERE id = ?", (phrase_id,))

    # ------------------------------------------------------------------- PFMP
    def pfmps(self, annee_id):
        with self.cx:
            for n in (1, 2):
                self.cx.execute("INSERT OR IGNORE INTO pfmp (annee_id, numero) VALUES (?,?)",
                                (annee_id, n))
        return self._tous("SELECT * FROM pfmp WHERE annee_id = ? ORDER BY numero", (annee_id,))

    def pfmp_id(self, annee_id, numero) -> int:
        return next(p["id"] for p in self.pfmps(annee_id) if p["numero"] == numero)

    def maj_pfmp(self, pfmp_id, debut, fin):
        self._x("UPDATE pfmp SET debut = ?, fin = ? WHERE id = ?",
                (debut.strip(), fin.strip(), pfmp_id))

    def enseignants(self, annee_id):
        rows = self._tous("SELECT * FROM enseignant WHERE annee_id = ?", (annee_id,))
        return sorted(rows, key=lambda e: normaliser(e["nom"]))

    def ajouter_enseignant(self, annee_id, nom) -> int:
        nom = " ".join(nom.split())
        if not nom:
            raise ValueError("Nom vide")
        r = self._un("SELECT id FROM enseignant WHERE annee_id = ? AND nom = ?", (annee_id, nom))
        if r:
            return r["id"]
        return self._x("INSERT INTO enseignant (annee_id, nom) VALUES (?,?)",
                       (annee_id, nom)).lastrowid

    def renommer_enseignant(self, enseignant_id, nom):
        nom = " ".join(nom.split())
        if not nom:
            raise ValueError("Nom vide")
        self._x("UPDATE enseignant SET nom = ? WHERE id = ?", (nom, enseignant_id))

    def supprimer_enseignant(self, enseignant_id):
        self._x("DELETE FROM enseignant WHERE id = ?", (enseignant_id,))

    def heures_classe(self, classe_id) -> dict:
        return {r["enseignant_id"]: r["heures"] for r in
                self._tous("SELECT * FROM repartition WHERE classe_id = ?", (classe_id,))}

    def heures_enseignant(self, enseignant_id) -> dict:
        return {r["classe_id"]: r["heures"] for r in
                self._tous("SELECT * FROM repartition WHERE enseignant_id = ?", (enseignant_id,))}

    def definir_heures(self, enseignant_id, classe_id, heures: float):
        if not heures or heures <= 0:
            self._x("DELETE FROM repartition WHERE enseignant_id = ? AND classe_id = ?",
                    (enseignant_id, classe_id))
        else:
            self._x("INSERT OR REPLACE INTO repartition (enseignant_id, classe_id, heures)"
                    " VALUES (?,?,?)", (enseignant_id, classe_id, float(heures)))

    _DEFAUT_STAGE = {"recherche": "en_cours", "convention": 0, "enseignant_id": None,
                     "entreprise": "", "adresse": "", "telephone": "", "tuteur": "",
                     "visite_le": ""}

    def stage(self, eleve_id, pfmp_id) -> dict:
        r = self._un("SELECT * FROM stage WHERE eleve_id = ? AND pfmp_id = ?", (eleve_id, pfmp_id))
        d = dict(self._DEFAUT_STAGE, eleve_id=eleve_id, pfmp_id=pfmp_id)
        if r:
            d.update(dict(r))
        return d

    def maj_stage(self, eleve_id, pfmp_id, **champs):
        champs = {k: v for k, v in champs.items() if k in self._DEFAUT_STAGE}
        if "convention" in champs:
            champs["convention"] = max(0, min(3, int(champs["convention"])))
        if "recherche" in champs and champs["recherche"] not in RECHERCHE:
            raise ValueError(champs["recherche"])
        with self.cx:
            self.cx.execute("INSERT OR IGNORE INTO stage (eleve_id, pfmp_id) VALUES (?,?)",
                            (eleve_id, pfmp_id))
            if champs:
                sets = ", ".join(f"{k} = ?" for k in champs)
                self.cx.execute(f"UPDATE stage SET {sets} WHERE eleve_id = ? AND pfmp_id = ?",
                                (*champs.values(), eleve_id, pfmp_id))
        if {"entreprise", "adresse", "telephone", "tuteur"} & set(champs):
            s = self.stage(eleve_id, pfmp_id)
            if s["entreprise"].strip():
                self.memoriser_entreprise(s["entreprise"], s["adresse"], s["telephone"], s["tuteur"])

    def stages(self, annee_id, pfmp_id):
        """Tous les élèves de l'année avec leur stage pour cette PFMP."""
        res = []
        stages = {r["eleve_id"]: dict(r) for r in
                  self._tous("SELECT * FROM stage WHERE pfmp_id = ?", (pfmp_id,))}
        ens = {e["id"]: e["nom"] for e in self.enseignants(annee_id)}
        suivies = {c["id"] for c in self.classes_pfmp(annee_id)}
        for e in self.eleves_annee(annee_id):
            if e["classe_id"] not in suivies:
                continue
            d = dict(self._DEFAUT_STAGE, eleve_id=e["id"], pfmp_id=pfmp_id)
            d.update(stages.get(e["id"], {}))
            d["nom"], d["prenom"] = e["nom"], e["prenom"]
            d["classe_id"], d["classe_nom"] = e["classe_id"], e["classe_nom"]
            d["enseignant_nom"] = ens.get(d["enseignant_id"], "")
            res.append(d)
        return res

    def suivis(self, enseignant_id, pfmp_id):
        return [s for s in self.stages(self._annee_enseignant(enseignant_id), pfmp_id)
                if s["enseignant_id"] == enseignant_id]

    def _annee_enseignant(self, enseignant_id):
        return self._un("SELECT annee_id FROM enseignant WHERE id = ?", (enseignant_id,))["annee_id"]

    def memoriser_entreprise(self, nom, adresse="", telephone="", tuteur=""):
        nom = nom.strip()
        if not nom:
            return
        r = self._un("SELECT * FROM entreprise WHERE nom = ?", (nom,))
        if r is None:
            self._x("INSERT INTO entreprise (nom, adresse, telephone, tuteur) VALUES (?,?,?,?)",
                    (nom, adresse.strip(), telephone.strip(), tuteur.strip()))
        else:
            # On ne remplace une information connue que par une information non vide.
            self._x("UPDATE entreprise SET adresse = ?, telephone = ?, tuteur = ? WHERE id = ?",
                    (adresse.strip() or r["adresse"], telephone.strip() or r["telephone"],
                     tuteur.strip() or r["tuteur"], r["id"]))

    def carnet(self, recherche=""):
        rows = self._tous("SELECT * FROM entreprise ORDER BY nom COLLATE NOCASE")
        mots = normaliser(recherche).split()
        if not mots:
            return list(rows)
        return [r for r in rows
                if all(m in normaliser(f"{r['nom']} {r['adresse']} {r['tuteur']}") for m in mots)]

    def entreprise(self, entreprise_id):
        return self._un("SELECT * FROM entreprise WHERE id = ?", (entreprise_id,))

    def stages_entreprise(self, nom) -> int:
        """Nombre de stages (toutes années) qui portent ce nom d'entreprise."""
        return self._un("SELECT COUNT(*) AS n FROM stage WHERE entreprise = ? COLLATE NOCASE",
                        (nom.strip(),))["n"]

    def ajouter_entreprise(self, nom, adresse="", telephone="", tuteur="") -> int:
        nom = " ".join(nom.split())
        if not nom:
            raise ValueError("Nom d'entreprise vide")
        if self._un("SELECT 1 FROM entreprise WHERE nom = ?", (nom,)):
            raise ValueError(f"« {nom} » est déjà dans le carnet")
        return self._x("INSERT INTO entreprise (nom, adresse, telephone, tuteur) VALUES (?,?,?,?)",
                       (nom, adresse.strip(), telephone.strip(), tuteur.strip())).lastrowid

    def maj_entreprise(self, entreprise_id, nom, adresse, telephone, tuteur, propager=False) -> int:
        """Modifie une fiche du carnet. Avec propager, reporte les changements sur les stages
        qui portent l'ancien nom (le tuteur seulement là où il était vide ou identique).
        -> nombre de stages mis à jour."""
        avant = self.entreprise(entreprise_id)
        if avant is None:
            raise ValueError("Entreprise introuvable")
        nom = " ".join(nom.split())
        if not nom:
            raise ValueError("Nom d'entreprise vide")
        autre = self._un("SELECT id FROM entreprise WHERE nom = ? AND id != ?", (nom, entreprise_id))
        if autre:
            raise ValueError(f"« {nom} » est déjà dans le carnet")
        adresse, telephone, tuteur = adresse.strip(), telephone.strip(), tuteur.strip()
        with self.cx:
            self.cx.execute("UPDATE entreprise SET nom = ?, adresse = ?, telephone = ?, tuteur = ?"
                            " WHERE id = ?", (nom, adresse, telephone, tuteur, entreprise_id))
            if not propager:
                return 0
            n = self.cx.execute(
                "UPDATE stage SET entreprise = ?, adresse = ?, telephone = ? WHERE entreprise = ? COLLATE NOCASE",
                (nom, adresse, telephone, avant["nom"])).rowcount
            self.cx.execute(
                "UPDATE stage SET tuteur = ? WHERE entreprise = ? COLLATE NOCASE AND (tuteur = '' OR tuteur = ?)",
                (tuteur, nom, avant["tuteur"]))
        return n

    def supprimer_entreprise(self, entreprise_id):
        """Retire la fiche du carnet ; les stages gardent leurs informations."""
        self._x("DELETE FROM entreprise WHERE id = ?", (entreprise_id,))

    # ------------------------------------------------------------------- JSON
    def exporter_json(self, chemin):
        donnees = {
            "format": FORMAT_JSON,
            "version": SCHEMA_VERSION,
            "exporte_le": maintenant(),
            "tables": {t: [dict(r) for r in self._tous(f"SELECT * FROM {t}")] for t in TABLES},
        }
        chemin = Path(chemin)
        tmp = chemin.with_suffix(chemin.suffix + ".tmp")
        tmp.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(chemin)
        return chemin

    def importer_json(self, chemin):
        """Remplace toutes les données par celles du fichier (une sauvegarde est faite avant)."""
        donnees = json.loads(Path(chemin).read_text(encoding="utf-8"))
        if donnees.get("format") not in FORMATS_ACCEPTES or not isinstance(donnees.get("tables"), dict):
            raise ValueError("Ce fichier n'est pas un export de Livret.")
        if int(donnees.get("version", 0)) > SCHEMA_VERSION:
            raise ValueError("Ce fichier provient d'une version plus récente de Livret.")
        self.sauvegarder("avant-import")
        self.cx.execute("PRAGMA foreign_keys = OFF")
        try:
            with self.cx:
                for t in reversed(TABLES):
                    self.cx.execute(f"DELETE FROM {t}")
                for t in TABLES:
                    colonnes = [r[1] for r in self.cx.execute(f"PRAGMA table_info({t})")]
                    for ligne in donnees["tables"].get(t, []):
                        cles = [k for k in ligne if k in colonnes]
                        if not cles:
                            continue
                        self.cx.execute(
                            f"INSERT INTO {t} ({', '.join(cles)}) VALUES ({', '.join('?' * len(cles))})",
                            [ligne[k] for k in cles])
                erreurs = self.cx.execute("PRAGMA foreign_key_check").fetchall()
                if erreurs:
                    raise ValueError("Le fichier contient des références incohérentes.")
        finally:
            self.cx.execute("PRAGMA foreign_keys = ON")
        self.annee_active()

    def archiver(self, annee_id) -> Path:
        """Exporte un instantané JSON puis passe l'année en lecture seule."""
        a = self.annee(annee_id)
        dossier = self.chemin.parent / "archives"
        dossier.mkdir(exist_ok=True)
        cible = dossier / f"livret-{a['libelle']}-{_dt.date.today():%Y%m%d}.json"
        self.archiver_annee(annee_id, True)
        self.exporter_json(cible)
        return cible
