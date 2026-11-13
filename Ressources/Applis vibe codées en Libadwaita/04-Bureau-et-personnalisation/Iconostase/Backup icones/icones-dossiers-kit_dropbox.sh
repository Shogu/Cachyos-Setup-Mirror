#!/usr/bin/env bash
# Pose les icônes de dossiers (attribut metadata::custom-icon, lu par Fichiers).
# Sans risque à relancer. Iconostase (0.2.3 et plus) reprend ensuite ces icônes dans sa sauvegarde.
set -u

KIT="$(cd "$(dirname "$0")" && pwd)"
# Les icônes vont directement dans le dossier d'Iconostase : ses sauvegardes les contiennent.
STORE="$HOME/.local/share/iconostase/dossiers"
ANCIEN="$HOME/.local/share/icones-dossiers"
D="$HOME/Dropbox"
T="$D/LYCEE/CLASSES/TERMINALE BAC PRO"
P="$D/LYCEE/CLASSES/1 BAC PRO"
S="$D/LYCEE/CLASSES/2 BAC PRO"

mkdir -p "$STORE"
cp -f "$KIT"/icones/*.svg "$STORE"/

ok=0
manquants=()

poser() {
    local icone="$1" dossier="$2"
    if [ ! -d "$dossier" ]; then
        manquants+=("$dossier")
        return
    fi
    gio set -t string "$dossier" metadata::custom-icon "file://$STORE/folder-$icone.svg" && ok=$((ok + 1))
}

creer_et_poser() {
    mkdir -p "$2"
    poser "$1" "$2"
}

poser casier          "$D/CASIER"
poser domestique      "$D/DOMESTIQUE"
poser concerts        "$D/DOMESTIQUE/concerts"
poser informatique    "$D/DOMESTIQUE/INFORMATIQUE"
poser backup          "$D/DOMESTIQUE/Emplacements backups et sauvegardes"
A="$D/DOMESTIQUE/ADMINISTRATIF"
poser administratif   "$A"
poser bpmc            "$A/BPMC"
poser auto            "$A/AUTO"
poser adeline         "$A/Adeline"
poser identite        "$A/IDENTITE"
poser adeline         "$A/IDENTITE/Adeline"
poser marla           "$A/IDENTITE/Marla"
poser velo            "$A/Velo"
poser impots          "$A/IMPOTS"
poser sante           "$A/SANTÉ"
poser marla           "$A/MARLA"
poser marla           "$D/MARLA"
poser vrac            "$D/VRAC"
poser public          "$D/Public"
poser notes           "$D/Notes"
poser lycee           "$D/Notes/Lycée"

poser lycee           "$D/LYCEE"
poser syndicat        "$D/LYCEE/SYNDICAT"
poser emploi-du-temps "$D/LYCEE/EDT & administratif"
poser a-classer       "$D/LYCEE/VRAC à classer"
poser a-classer       "$D/Dropboxable/Dropboxable 2025/A trier"
poser epreuves-bac-note "$D/LYCEE/Dropboxable/Bac Blanc 2026"
poser epreuves-bac-note "$D/Dropboxable/Dropboxable 2025/Bac Blanc 2026"

poser classe-2nde      "$S"
poser classe-1re       "$P"
poser classe-terminale "$T"
for classe in "$S" "$P" "$T"; do
    poser francais       "$classe/FRANCAIS"
    poser histoire       "$classe/HISTOIRE"
    poser geo            "$classe/GEOGRAPHIE"
    poser cointervention "$classe/CO-INTERVENTION"
done
poser emc             "$T/EMC"
E="$T/Epreuves type BAC"
poser epreuves-bac-officiel "$E"
poser epreuves-bac-officiel "$E/Bac Juin 2026"
poser epreuves-bac-officiel "$E/Sujet Bac de rentrée"
poser epreuves-bac-note     "$E/Bacs Blancs"
poser 2025            "$E/Bacs Blancs/2025"
poser 2026            "$E/Bacs Blancs/2026"

for annee in 2025 2026 2027 2028 2029 2030; do
    creer_et_poser "$annee" "$D/Dropboxable/Dropboxable $annee"
done

poser dot-local       "$HOME/.local"
poser dot-config      "$HOME/.config"
poser applications    "$HOME/.local/share/applications"
poser icons           "$HOME/.local/share/icons"
poser fish            "$HOME/.config/fish"
poser extensions      "$HOME/.local/share/gnome-shell/extensions"
poser bin             "$HOME/.local/bin"

auto=$(python3 - "$STORE" "$ANCIEN" "$D/LYCEE" "$D/Dropboxable" <<'PY'
import os
import re
import sys
import unicodedata

from gi.repository import Gio

store, ancien, roots = sys.argv[1], sys.argv[2], sys.argv[3:]
ATTRIBUTE = "metadata::custom-icon"
RULES = [
    ("theme", r"^theme\s*(\d+\s*)?-"),
    ("sequence", r"^sequence\s*(\d+\s*)?-"),
    ("intro", r"^(intro(duction)?\b|s(e|__)ances? introducti)"),
    ("seance", r"^s(e|__)ances?\b"),
    ("evaluation", r"^evaluations?\b"),
    ("trace-ecrite", r"^traces? ecrites?"),
    ("ressources", r"^ressources\b"),
    ("corpus", r"^(corpus|documents?|documentation)\b"),
    ("ebook", r"^e-?books?\b"),
    ("audiobook", r"^(audiobooks?|livres? audio)\b"),
    ("bd", r"^bd\b"),
    ("videos", r"^(videos?|extraits? video)\b"),
    ("methodo", r"^(methodos?|methodes?|methodologie)\b"),
    ("accompagnement", r"^accompagnement perso"),
    ("images", r"^images?\b"),
    ("cartes", r"^(cartes?|carto(graphie)?s?)\b"),
]


def plain(text):
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()


def apply(path, icon):
    folder = Gio.File.new_for_path(path)
    current = folder.query_info(ATTRIBUTE, Gio.FileQueryInfoFlags.NONE, None).get_attribute_string(ATTRIBUTE)
    if current and not (Gio.File.new_for_uri(current).get_path() or "").startswith((store, ancien)):
        return 0
    target = Gio.File.new_for_path(os.path.join(store, f"folder-{icon}.svg")).get_uri()
    folder.set_attribute_string(ATTRIBUTE, target, Gio.FileQueryInfoFlags.NONE, None)
    return 1


count = 0
for root in roots:
    for parent, dirs, _files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in dirs:
            icon = next((icon for icon, pattern in RULES if re.search(pattern, plain(name))), None)
            if icon is None or (icon == "images" and ("js" in dirs or "medias" in dirs)):
                continue
            number = re.match(r"^s(e|__)ances?\s*(\d+)", plain(name))
            if icon == "seance" and number and 1 <= int(number.group(2)) <= 5:
                icon = f"seance-{int(number.group(2))}"
            count += apply(os.path.join(parent, name), icon)
print(count)
PY
)
# Met à jour la liste d'Iconostase pour qu'elle suive les icônes posées ici (Iconostase doit être fermé).
python3 - "$STORE" <<'PY'
import json
import os
import sys

from gi.repository import Gio

store = sys.argv[1]
plan_path = os.path.join(os.path.dirname(store), "dossiers.json")
if os.path.isfile(plan_path):
    with open(plan_path, encoding="utf-8") as file:
        plan = json.load(file)
    for folder in plan["dossiers"]:
        path = os.path.join(os.path.expanduser("~"), folder["chemin"])
        if not os.path.isdir(path):
            continue
        uri = Gio.File.new_for_path(path).query_info("metadata::custom-icon", Gio.FileQueryInfoFlags.NONE, None).get_attribute_string("metadata::custom-icon")
        icon = Gio.File.new_for_uri(uri).get_path() if uri else None
        if icon and os.path.dirname(icon) == store:
            folder["icone"] = os.path.basename(icon)
    with open(plan_path, "w", encoding="utf-8") as file:
        json.dump(plan, file, ensure_ascii=False, indent=1)
PY
echo "$ok icônes posées sur les dossiers nommés, ${auto:-0} sur les sous-dossiers de séquences."
if [ ${#manquants[@]} -gt 0 ]; then
    echo "Dossiers introuvables, laissés de côté :"
    printf '  %s\n' "${manquants[@]}"
fi
echo "Si Fichiers affiche encore les anciennes icônes : nautilus -q, puis rouvre-le."
