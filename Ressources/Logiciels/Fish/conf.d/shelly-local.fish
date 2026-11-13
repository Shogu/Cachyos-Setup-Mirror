# shelly install standard ./<Tab> : réactive la complétion de fichiers
# dès que le mot en cours contient un « / » (./, ../, ~/, /chemin…)
complete -c shelly \
    -n '__fish_seen_subcommand_from install; and __fish_seen_subcommand_from standard; and string match -q -- "*/*" (commandline -ct)' \
    -F
