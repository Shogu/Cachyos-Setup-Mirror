"""Fenêtre de préférences : chaque option de l'appli peut être activée ou désactivée."""

from gi.repository import Adw, Gio, Gtk

GROUPS = [
    ("Lecture", "dialog-information-symbolic", [
        ("link-preview", "Aperçu des liens au survol", "Résumé et vignette de l'article lié"),
        ("dictionary", "Définition au double-clic", "Bulle du Wiktionnaire sur le mot cliqué"),
        ("hide-references", "Masquer notes, références et annexes", "Lecture épurée, sans appels de notes"),
        ("search-history", "Historique dans la barre de recherche", "Articles récents, effaçables un par un ou en bloc"),
    ]),
    ("Panneaux", "sidebar-show-symbolic", [
        ("show-toc", "Sommaire latéral", None),
        ("show-key-dates", "Dates clés", "Repères chronologiques tirés de Wikidata"),
        ("show-map", "Carte des lieux", "Carte OpenStreetMap de l'article ; clic droit sur un nom de lieu pour le situer"),
        ("show-related", "Voir aussi", "Section « Voir aussi » de l'article et articles proches"),
        ("reperes-auto", "Ouvrir le panneau Repères automatiquement", "Quand l'article a des dates clés ou une carte"),
        ("maps-button", "Ouvrir dans Cartes", "Bouton de la carte et clic droit sur un nom de lieu ; masqué si GNOME Cartes est absent"),
    ]),
    ("Sources", "system-search-symbolic", [
        ("enable-vikidia", "Vikidia", "Encyclopédie des 8-13 ans : articles plus courts et plus simples"),
        ("enable-wikisource", "Textes", "Œuvres et documents historiques de Wikisource"),
        ("enable-commons", "Images", "Images en haute définition de Wikimedia Commons"),
        ("pellicola-button", "Bouton « Ouvrir dans Pellicola »", "Masqué de toute façon si Pellicola est absente"),
    ]),
    ("Panier et export", "document-save-symbolic", [
        ("basket-numbered", "Numéroter les documents", "Document 1, 2… avec légende, source sous chaque document"),
        ("basket-source", "Ajouter la source", "Ligne de crédit discrète : titre, lien, licence CC BY-SA"),
        ("pdf-images", "Images dans l'export PDF d'un article", None),
        ("pdf-toc", "Sommaire dans l'export PDF d'un article", None),
    ]),
]


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, settings):
        super().__init__(title="Préférences", search_enabled=True)
        page = Adw.PreferencesPage(title="Général", icon_name="preferences-system-symbolic")
        self.add(page)
        for title, _icon, rows in GROUPS:
            group = Adw.PreferencesGroup(title=title)
            for key, label, sub in rows:
                row = Adw.SwitchRow(title=label)
                if sub:
                    row.set_subtitle(sub)
                settings.bind(key, row, "active", Gio.SettingsBindFlags.DEFAULT)
                group.add(row)
            if title == "Lecture":
                combo = Adw.ComboRow(title="Copie par défaut (Ctrl+C)",
                                     subtitle="Ctrl+Maj+C copie dans l'autre format",
                                     model=Gtk.StringList.new(["Texte mis en forme", "Texte brut"]))
                combo.set_selected(0 if settings.get_string("copy-format") == "rich" else 1)
                combo.connect("notify::selected", lambda c, _p: settings.set_string(
                    "copy-format", "rich" if c.get_selected() == 0 else "plain"))
                group.add(combo)
                widths = [("normal", "Normale"), ("wide", "Large"), ("full", "Pleine largeur")]
                wrow = Adw.ComboRow(title="Largeur du texte",
                                    subtitle="Aussi dans le menu principal",
                                    model=Gtk.StringList.new([w[1] for w in widths]))
                cur = settings.get_string("reading-width")
                wrow.set_selected(next((i for i, w in enumerate(widths) if w[0] == cur), 0))
                wrow.connect("notify::selected", lambda r, _p: settings.set_string(
                    "reading-width", widths[r.get_selected()][0]))
                group.add(wrow)
            page.add(group)
