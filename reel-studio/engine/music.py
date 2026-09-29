"""Music for reels: the user describes it, we generate options to audition.

Providers:
  - "free" (default): the built-in composer (engine/musicgen.py) — offline, instant,
    royalty-free, included for everyone. Good background beds (lo-fi, jazz café, pop,
    amapiano, cinematic…).
  - "elevenlabs": Eleven Music API (cleared for commercial use incl. social media;
    https://elevenlabs.io/docs/api-reference/music/compose). Needs ELEVENLABS_API_KEY in the
    environment or in brand/.env. Paid per generation — we always say so before generating.
  - "own": the user's own track dropped in inbox/ (free).
Generated files land in projects/<p>/music/ and are picked in the Studio or by Claude.
"""
import json, os, re, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MOODS = ["cosy", "dreamy", "uplifting", "confident", "calm", "playful", "romantic", "nostalgic",
         "motivational", "chic", "mysterious", "sunny", "emotional", "energetic"]
GENRES = ["lo-fi", "acoustic", "indie pop", "soft piano", "jazz café", "bossa nova", "r&b",
          "house", "cinematic", "funk", "afrobeats", "amapiano", "ambient", "synth-pop"]


def build_prompt(brief, duration_s):
    """Turn the questionnaire answers into a clear music prompt.
    brief: {"mood": [...], "genre": [...], "tempo": "slow|medium|fast"|bpm, "instruments": "...",
            "energy": "steady|build|drop", "describe": "free text", "vocals": false}"""
    mood = ", ".join(brief.get("mood", [])) or "warm"
    genre = ", ".join(brief.get("genre", [])) or "indie pop"
    tempo = brief.get("tempo", "medium")
    bpm = {"slow": "70-85 BPM", "medium": "95-110 BPM", "fast": "120-128 BPM"}.get(str(tempo), f"{tempo} BPM")
    energy = {"steady": "steady energy throughout",
              "build": "starts gentle and builds to a lift in the last third",
              "drop": "short intro then a satisfying drop around the middle"}.get(brief.get("energy", "steady"), "")
    parts = [f"{mood} {genre} background track for a {int(duration_s)}-second vertical social video",
             bpm, energy]
    if brief.get("instruments"):
        parts.append(f"featuring {brief['instruments']}")
    if brief.get("describe"):
        parts.append(brief["describe"])
    parts.append("clean mix that sits under a speaking voice, no sudden loud peaks, loop-friendly ending")
    if not brief.get("vocals"):
        parts.append("instrumental, no vocals")
    return ". ".join(p for p in parts if p)


def _api_key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    env = os.path.join(ROOT, "brand", ".env")
    if os.path.exists(env):
        for line in open(env):
            m = re.match(r"\s*ELEVENLABS_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return None


def available():
    return {"free": True, "elevenlabs": bool(_api_key()), "own": True}


def generate_free(brief, duration_s, out_path, seed=None):
    from . import musicgen
    stereo, desc = musicgen.compose(brief, duration_s, seed=seed)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    musicgen.write(out_path, stereo)
    return out_path, desc


def generate_elevenlabs(prompt, duration_s, out_path, instrumental=True):
    key = _api_key()
    if not key:
        raise RuntimeError("No ElevenLabs API key. Add ELEVENLABS_API_KEY=... to brand/.env")
    body = json.dumps({"prompt": prompt, "music_length_ms": int(min(max(duration_s, 3), 600) * 1000),
                       "force_instrumental": bool(instrumental)}).encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128", data=body,
                                 headers={"xi-api-key": key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Music generation failed ({e.code}): {e.read()[:300]!r}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "wb").write(data)
    return out_path


def generate(project_dir, brief, duration_s, options=2, provider=None):
    """Generate `options` tracks for a project. Returns list of file paths + the prompt used.
    provider: "free" (built-in, default) or "elevenlabs" (needs a key, paid per track)."""
    provider = provider or brief.get("provider") or ("free" if not _api_key() else "free")
    prompt = build_prompt(brief, duration_s)
    outs = []
    if provider == "free":
        descs = []
        for i in range(options):
            p, d = generate_free(brief, duration_s, os.path.join(project_dir, "music", f"option-{i + 1}.wav"), seed=i * 7 + 1)
            outs.append(p)
            descs.append(d)
        json.dump({"provider": "free", "brief": brief, "files": [os.path.basename(o) for o in outs], "descriptions": descs},
                  open(os.path.join(project_dir, "music", "brief.json"), "w"), indent=1)
        return outs, " | ".join(descs)
    for i in range(options):
        p = os.path.join(project_dir, "music", f"option-{i + 1}.mp3")
        generate_elevenlabs(prompt + (f". Variation {i + 1}." if i else ""), duration_s, p,
                            instrumental=not brief.get("vocals"))
        outs.append(p)
    json.dump({"prompt": prompt, "brief": brief, "files": [os.path.basename(o) for o in outs]},
              open(os.path.join(project_dir, "music", "brief.json"), "w"), indent=1)
    return outs, prompt
