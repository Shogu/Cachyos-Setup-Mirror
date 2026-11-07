"""Icônes Ogu, version autonome : tout est dans ce fichier, rien à installer.
Lancement : python3 icones-ogu.pyz"""
import os, sys, zipfile, hashlib, runpy
from pathlib import Path

archive = Path(os.path.dirname(os.path.abspath(__file__)))     # = le fichier .pyz lui-même
stamp = hashlib.sha1(f"{archive.stat().st_size}-{archive.stat().st_mtime}".encode()).hexdigest()[:12]
cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "icones-ogu" / stamp
if not (cache / ".ok").exists():
    with zipfile.ZipFile(archive) as z:
        for m in z.namelist():
            if m.startswith("bundle/") and not m.endswith("/"):
                dst = cache / m[len("bundle/"):]
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(z.read(m))
    (cache / "icones.sh").chmod(0o755)
    (cache / ".ok").touch()
os.environ["ICONES_OGU_DIR"] = str(cache)
sys.argv[0] = str(cache / "icones-ogu.py")
runpy.run_path(str(cache / "icones-ogu.py"), run_name="__main__")
