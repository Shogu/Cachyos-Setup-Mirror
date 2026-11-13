# Grille

Visionneuse simple de fichiers tableurs, codée avec Claude.

## État

- Seul `README.md` est présent. Le paquet attendu `grille-0.1.0-1-x86_64.pkg.tar.zst` est **à déposer manuellement par Ogu** ; ne pas l'inventer ni créer de faux paquet.
- Formats pris en charge, langage, app id et commande de lancement : **inconnus** tant que le paquet n'est pas là. Le paquet étant `x86_64`, il est probablement compilé (pas du Python pur).
- Quand le paquet arrive : l'inspecter (`bsdtar -xOf <pkg> .PKGINFO`, `bsdtar -tf <pkg>`), puis compléter ce fichier, `README.md` et `docs/11-applications-vibe-coded.md` §11.24 avec les informations réelles.
