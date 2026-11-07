from __future__ import annotations

import sys


def main() -> int:
    try:
        from .app import main as app_main
    except ModuleNotFoundError as exc:
        if exc.name == "gi":
            print(
                "PyGObject/libadwaita est absent. Sur CachyOS/Arch :\n"
                "  sudo pacman -S --needed gtk4 libadwaita python-gobject",
                file=sys.stderr,
            )
            return 1
        raise
    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
