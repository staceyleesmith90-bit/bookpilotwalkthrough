"""Publish an update every subscriber gets automatically (within a day).

    python scripts/make_release.py "New: 20 caption styles, faster renders"   -> dist/release-<version>.zip

Then (Gert / Stacey-Lee, once per release):
  1. npx wrangler r2 object put reel-releases/releases/<version>.zip --file dist/release-<version>.zip
  2. curl -X POST https://reelstudio.systemspilot.co.za/api/admin/release -H "Authorization: Bearer $ADMIN_TOKEN" \\
       -H "Content-Type: application/json" -d @dist/release-<version>.json
Bump VERSION first. Only the app goes in the zip (engine, skills, library, docs) — never anyone's files.
If the release needs new Python packages, also set "min_extension" to this version and publish a new .mcpb:
people on older installers are then asked to download it instead of half-updating.
"""
import hashlib, json, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = ["engine", "library", ".claude", "docs", "VERSION", "AGENTS.md", "CLAUDE.md", "requirements.txt", "scripts"]
SKIP_LIB = {"emoji-cache", "models", "cache"}


def build(notes="", min_extension="0"):
    version = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"release-{version}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for top in APP:
            p = os.path.join(ROOT, top)
            if os.path.isfile(p):
                z.write(p, top)
                continue
            for d, dirs, files in os.walk(p):
                rel = os.path.relpath(d, ROOT).replace(os.sep, "/")
                dirs[:] = [x for x in dirs if x != "__pycache__" and not (rel == "library" and x in SKIP_LIB)]
                for f in files:
                    if not f.endswith(".pyc"):
                        z.write(os.path.join(d, f), f"{rel}/{f}")
    data = open(out, "rb").read()
    meta = {"version": version, "notes": notes, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
            "min_extension": min_extension}
    json.dump(meta, open(out.replace(".zip", ".json"), "w"), indent=1)
    return out, meta


if __name__ == "__main__":
    out, meta = build(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else "0")
    print(out, f"{meta['size'] / 1e6:.1f} MB", meta["sha256"][:12])
