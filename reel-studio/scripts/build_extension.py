"""Build the one-click Claude Desktop extension: dist/reel-studio-<version>.mcpb

    python scripts/build_extension.py

The .mcpb is a zip: manifest.json + pyproject.toml (Claude installs the Python packages itself) +
src/ (the small local server) + app/ (the engine, library, playbooks). Customers double-click it in
Claude Desktop (Windows or Mac), paste their licence key, done.
"""
import json, os, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "extension")
APP_ITEMS = ["engine", "library", ".claude", "docs", "VERSION", "AGENTS.md", "CLAUDE.md", "requirements.txt", "scripts"]
SKIP_DIRS = {"__pycache__", "cache", "models", "emoji-cache", ".pytest_cache"}


def make_icon(path):
    from PIL import Image, ImageDraw, ImageFont
    s = 512
    im = Image.new("RGBA", (s, s))
    grad = Image.new("RGBA", (s, s))
    stops = [(0, (0, 181, 217)), (0.38, (30, 99, 255)), (0.7, (106, 17, 203)), (1, (236, 72, 153))]
    px = grad.load()
    for x in range(s):
        for y in range(s):
            t = (x * 0.8 + y * 0.2) / s
            for (a, ca), (b, cb) in zip(stops, stops[1:]):
                if a <= t <= b:
                    k = (t - a) / (b - a)
                    px[x, y] = tuple(int(ca[i] + (cb[i] - ca[i]) * k) for i in range(3)) + (255,)
                    break
    mask = Image.new("L", (s, s))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=112, fill=255)
    im.paste(grad, (0, 0), mask)
    font = ImageFont.truetype(os.path.join(ROOT, "library", "fonts", "Poppins-ExtraBold.ttf"), 330)
    ImageDraw.Draw(im).text((s / 2, s / 2 + 10), "S", font=font, fill="white", anchor="mm")
    im.save(path)


def main():
    version = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
    man = json.load(open(os.path.join(EXT, "manifest.json"), encoding="utf-8"))
    man["version"] = version
    tester = "--tester-until" in sys.argv                  # private tester build: no key needed until a date
    if tester:
        until = sys.argv[sys.argv.index("--tester-until") + 1]
        man["server"]["mcp_config"]["env"]["REEL_TESTER_UNTIL"] = until
        man["user_config"]["licence_key"]["required"] = False
        man["display_name"] += " (tester)"
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"reel-studio-{version}" + ("-tester" if tester else "") + ".mcpb")
    icon = os.path.join(EXT, "icon.png")
    if not os.path.exists(icon):
        make_icon(icon)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(man, indent=2))
        for name in ("pyproject.toml", ".mcpbignore", "icon.png"):
            z.write(os.path.join(EXT, name), name)
        for dp, dns, fns in os.walk(os.path.join(EXT, "src")):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                if not fn.endswith(".pyc"):
                    full = os.path.join(dp, fn)
                    z.write(full, os.path.relpath(full, EXT))
        for item in APP_ITEMS:
            src = os.path.join(ROOT, item)
            if os.path.isfile(src):
                z.write(src, f"app/{item}")
                continue
            for dp, dns, fns in os.walk(src):
                dns[:] = [d for d in dns if d not in SKIP_DIRS]
                for fn in fns:
                    if fn.endswith(".pyc"):
                        continue
                    full = os.path.join(dp, fn)
                    if os.path.islink(full):
                        continue
                    z.write(full, "app/" + os.path.relpath(full, ROOT).replace(os.sep, "/"))
    print(f"built {os.path.relpath(out, ROOT)} ({os.path.getsize(out) / 1e6:.1f} MB)")
    return out


if __name__ == "__main__":
    main()
