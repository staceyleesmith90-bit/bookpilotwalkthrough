"""A short problem report the user can email to support — nothing private in it.

No footage, no transcripts, no brand files, no licence key: only versions, what's installed,
the computer type, and the last error lines Reel Studio logged.
"""
import glob, io, os, platform, re, time
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _scrub(t):
    t = re.sub(r"(?i)(key|token|secret|password)\S*\s*[:=]\s*\S+", r"\1=<hidden>", t)
    return t.replace(os.path.expanduser("~"), "~")


def write():
    from .__main__ import setup_check
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            setup_check()
        except Exception as e:
            print("setup-check failed:", e)
    errs = []
    for f in sorted(glob.glob(os.path.join(ROOT, "projects", "*", "renders", "*.log")), key=os.path.getmtime)[-3:]:
        lines = open(f, encoding="utf-8", errors="ignore").read().splitlines()
        errs += [f"[{os.path.basename(os.path.dirname(os.path.dirname(f)))}] " + l for l in lines
                 if re.search(r"error|traceback|failed", l, re.I)][-8:]
    ver = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
    text = (f"Reel Studio problem report — {time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Version {ver} · {platform.system()} {platform.release()} · {platform.machine()} · Python {platform.python_version()}\n\n"
            f"What's installed:\n{buf.getvalue()}\nRecent errors:\n" + ("\n".join(errs) or "(none logged)") +
            "\n\nWhat happened (in your words):\n\n")
    out = os.path.join(ROOT, "out", "problem-report.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(_scrub(text))
    return out
