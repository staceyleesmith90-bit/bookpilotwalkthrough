"""Bundle the Phosphor icon set (MIT) into library/icons/ so stickers work offline.

    python scripts/fetch_icons.py            # regular, bold, fill, duotone, thin

Writes library/icons/index.json ({name: [tags...]}) and library/icons/<weight>/<name>.svg.
Re-run any time to update to the latest Phosphor release.
"""
import json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "library", "icons")
BASE = "https://raw.githubusercontent.com/phosphor-icons/core/main/"
WEIGHTS = sys.argv[1:] or ["regular", "bold", "fill", "duotone", "thin"]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "reel-studio"}), timeout=30) as r:
        return r.read()


def main():
    ts = get(BASE + "src/icons.ts").decode()
    index = {}
    for block in re.findall(r"\{\s*name:\s*\"([^\"]+)\".*?tags:\s*\[(.*?)\]", ts, re.S):
        name, tags = block
        index[name] = [t for t in re.findall(r"\"([^\"]+)\"", tags) if not t.startswith("*")]
    os.makedirs(OUT, exist_ok=True)
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), separators=(",", ":"))
    open(os.path.join(OUT, "LICENSE"), "wb").write(get(BASE + "LICENSE"))

    def fetch(args):
        w, n = args
        path = os.path.join(OUT, w, f"{n}.svg")
        if os.path.exists(path):
            return
        fname = n if w == "regular" else f"{n}-{w}"
        try:
            open(path, "wb").write(get(f"{BASE}assets/{w}/{fname}.svg"))
        except Exception as e:
            print("skip", w, n, e)

    jobs = []
    for w in WEIGHTS:
        os.makedirs(os.path.join(OUT, w), exist_ok=True)
        jobs += [(w, n) for n in index]
    with ThreadPoolExecutor(32) as ex:
        list(ex.map(fetch, jobs))
    print(f"{len(index)} icons x {len(WEIGHTS)} weights -> {OUT}")


if __name__ == "__main__":
    main()
