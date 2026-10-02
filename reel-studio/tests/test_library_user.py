import json, os

from engine import library_user as lu, project


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(lu, "FAV", str(tmp_path / "brand" / "favourites.json"))
    monkeypatch.setattr(lu, "INBOX", str(tmp_path / "inbox"))
    monkeypatch.setattr(lu, "TRASH", str(tmp_path / "trash"))
    monkeypatch.setattr(project, "PROJECTS", str(tmp_path / "projects"))
    (tmp_path / "inbox").mkdir()


def test_favourites_toggle(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    assert lu.toggle_favourite("filter", "warm-film", "Warm film") is True
    assert [f["id"] for f in lu.favourites()] == ["warm-film"]
    assert lu.toggle_favourite("filter", "warm-film", "Warm film") is False
    assert lu.favourites() == []


def test_uploads_trash_and_restore(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    (tmp_path / "inbox" / "clip.mp4").write_bytes(b"x")
    (tmp_path / "inbox" / "song.mp3").write_bytes(b"y")
    kinds = {u["name"]: u["kind"] for u in lu.uploads()}
    assert kinds == {"clip.mp4": "video", "song.mp3": "sound"}
    tid = lu.to_trash("upload", "song.mp3")
    assert [u["name"] for u in lu.uploads()] == ["clip.mp4"]
    assert lu.trash_list()[0]["days_left"] == 30
    assert lu.restore(tid) == "song.mp3" and (tmp_path / "inbox" / "song.mp3").exists()
    assert lu.trash_list() == []
    try:
        lu.upload_path("../secret")
        assert False
    except (ValueError, FileNotFoundError):
        pass


def test_reel_to_trash_and_back(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    d = tmp_path / "projects" / "my-reel"
    d.mkdir(parents=True)
    (d / "project.json").write_text(json.dumps({"slug": "my-reel"}))
    tid = lu.to_trash("reel", "my-reel", "My reel")
    assert not d.exists()
    lu.restore(tid)
    assert (d / "project.json").exists()
    lu.to_trash("reel", "my-reel")
    assert lu.empty_trash() == 1 and lu.trash_list() == []


def test_notifications_from_disk(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(lu, "_update_note", {"t": 9e18, "note": None})
    d = tmp_path / "projects" / "done-reel"
    (d / "renders").mkdir(parents=True)
    (d / "project.json").write_text(json.dumps({"slug": "done-reel", "source": "x.mp4"}))
    (d / "brief.json").write_text(json.dumps({"topic": "Morning routine"}))
    (d / "renders" / "final.mp4").write_bytes(b"v")
    n = lu.notifications({"done-reel": {"state": "error"}})
    assert any("Morning routine" in x["text"] and "finished" in x["text"] for x in n)
    assert any("went wrong" in x["text"] for x in n)
