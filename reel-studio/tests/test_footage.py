import os

from engine import footage


def test_drive_ids_from_every_link_shape():
    for link, want in [("https://drive.google.com/drive/folders/1-HY7XcnVyxJzazwquqyg7w8ypoeOVW38?usp=sharing", "1-HY7XcnVyxJzazwquqyg7w8ypoeOVW38"),
                       ("https://drive.google.com/file/d/1RkPzqzR7Jq0IDbaJOm3CGg9KOHgDsD5e/view?usp=sharing", "1RkPzqzR7Jq0IDbaJOm3CGg9KOHgDsD5e"),
                       ("https://drive.google.com/open?id=1RkPzqzR7Jq0IDbaJOm3CGg9KOHgDsD5e", "1RkPzqzR7Jq0IDbaJOm3CGg9KOHgDsD5e")]:
        assert footage._ID.search(link).group(1) == want


def test_local_folder_copies_only_new_media(tmp_path):
    src = tmp_path / "synced"
    src.mkdir()
    (src / "a.mov").write_bytes(b"x")
    (src / "b.JPG").write_bytes(b"x")
    (src / "notes.txt").write_text("no")
    dest = tmp_path / "out"
    assert sorted(footage.fetch(None, str(src), str(dest))) == ["a.mov", "b.JPG"]
    assert footage.fetch(None, str(src), str(dest)) == []
    assert not os.path.exists(dest / "notes.txt")
