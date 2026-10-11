"""Reel Studio engine."""
import atexit, os, shutil, tempfile, time

# Every working file the engine makes goes in one folder per run, removed when the run ends, so reels never
# fill up the person's computer. Folders left behind by a crash are swept a day later.
_base = tempfile.gettempdir()
try:
    for _d in os.listdir(_base):
        _p = os.path.join(_base, _d)
        if _d.startswith("reel-studio-") and time.time() - os.path.getmtime(_p) > 86400:
            shutil.rmtree(_p, ignore_errors=True)
    _run_dir = tempfile.mkdtemp(prefix="reel-studio-")
    tempfile.tempdir = _run_dir
    atexit.register(shutil.rmtree, _run_dir, True)
except OSError:
    pass
