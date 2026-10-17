import json
from engine import chat, motiongfx, packs, project, sounddesign
from engine.plan import to_timeline


def test_every_kind_renders_and_settles():
    pk = packs.load("minimal")
    for kind in motiongfx.KINDS:
        r = motiongfx.render(kind, {}, pk)
        assert r["frames"] and r["frames"][-1][1] > 100          # last frame holds
        assert r["frames"][0][0].size == r["frames"][-1][0].size  # cropped once, same box
        assert r["sfx"] and all(ev in sounddesign.KITS for _, ev in r["sfx"])


def test_motion_kit_events_resolve_to_real_recordings():
    for ev in ("pill_in", "window_in", "toggle", "chart_grow", "tick", "click", "air", "notify", "thump"):
        f = sounddesign.source_file(f"sd:motion:{ev}:1")[0]
        assert not f.startswith("s:"), ev


def test_plan_mg_beat_and_motion_sound():
    plan = {"format": "faceless", "pack": "minimal", "sound": "motion",
            "beats": [{"text": "three checks", "dur": 2.0, "do": ["mg:pills"], "mg": {"labels": ["a", "b", "c"]}},
                      {"text": "next", "dur": 1.5, "do": ["mg:toggle"], "mg": {"label": "on"}}]}
    tl = to_timeline(plan)
    mg = [i for i in tl["items"] if i["type"] == "mg"]
    assert [i["kind"] for i in mg] == ["pills", "toggle"]
    names = {s["name"].split(":")[2] for s in tl["audio"]["sfx"]}
    assert {"pill_in", "toggle"} <= names and "whoosh" not in names
    assert not any(i.get("role") == "takeover" for i in tl["items"])
    assert tl["end_card"].get("sound") is False


def test_chat_saves_request_when_claude_is_not_available(monkeypatch):
    slug = project.new(None, "pytest-chat")
    try:
        monkeypatch.setattr(chat, "available", lambda: False)
        r = chat.send(slug, "make the title bigger")
        assert r["state"] == "done" and "Saved" in r["reply"]
        assert ("pytest-chat" in slug) and chat.inbox(slug) == [(slug, "make the title bigger")]
        h = chat.history(slug)["messages"]
        assert [m["role"] for m in h] == ["you", "claude"]
    finally:
        import shutil
        shutil.rmtree(project.path(slug), ignore_errors=True)
