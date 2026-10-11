# dconf-editor GTK4

**Pas une app vibe codée** : build de la branche upstream `use-gtk-4` de https://gitlab.gnome.org/GNOME/dconf-editor, empaqueté localement.

- Paquet : `dconf-editor-gtk4` (x86_64), `provides`/`conflicts` = `dconf-editor`, groupe `gnome-extra`.
- Langage **Vala**, build **Meson + Ninja** (`makedepends` : meson, ninja, vala, pkgconf, gettext). App id `ca.desrt.dconf-editor`.
- Dépendances : gtk4 ≥ 4.14.2, libadwaita ≥ 1.6, dconf, glib2.
- Pas de readme dans ce dossier ; la doc est dans `docs/11-applications-vibe-coded.md` §11.15 (le paquet GTK3 des dépôts doit être retiré avant).
- Ne pas y ajouter de fonctions maison : pour une mise à jour, recompiler depuis upstream (PKGBUILD type `meson setup build --prefix=/usr && meson compile -C build && meson install -C build --destdir "$pkgdir"`) et incrémenter la version.
- Toujours le présenter comme « build upstream », distinct des forks vibe codés.
