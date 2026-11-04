from PIL import Image

from engine import cover


def test_defaults_from_first_title_scene():
    tl = {"scenes": [{"spec": {"overlay": True}}, {"spec": {"title": "speel saam", "kicker": "boetie en sussie"}}]}
    assert cover.defaults(tl) == ("speel saam", "boetie en sussie")
    assert cover.spec_of(tl)["title"] == "speel saam"


def test_cover_can_be_switched_off_and_overridden():
    assert cover.spec_of({"cover": {"enabled": False}, "scenes": [{"spec": {"title": "x"}}]}) is None
    sp = cover.spec_of({"cover": {"title": "mine"}, "scenes": [{"spec": {"title": "x", "kicker": "k"}}]})
    assert sp["title"] == "mine" and sp["kicker"] == "k"


def test_design_draws_text_over_photo():
    pic = Image.new("RGB", (900, 1600), (120, 160, 200))
    im = cover.design(pic, "a long cover title that wraps", "kicker", {"pop": "#A98BD6"}, 540, 960, 0.7)
    assert im.size == (540, 960)
    assert im.getpixel((270, 50)) == (120, 160, 200)          # picture untouched away from the text
    assert len(set(im.crop((0, 560, 540, 780)).getdata())) > 50   # text + shade drawn
