import json, shutil
from PIL import Image
from engine import postkit, project


def test_memory_posts_use_the_reels_look_and_layouts(tmp_path):
    slug = project.new(None, "pytest-memory-posts")
    try:
        src = project.path(slug, "source")
        for i in range(3):
            Image.new("RGB", (600, 800), (200, 120 + 30 * i, 140)).save(f"{src}/p{i}.jpg")
        project.save(slug, "plan.json", {"pack": "blush", "beats": []})
        rel = lambda i: f"projects/{slug}/source/p{i}.jpg"
        project.save(slug, "posts.json", {"style": "memory", "caption": "liefde",
            "carousel": [{"layout": "photo", "photo": rel(0), "title": "Liara is 8 maande!", "kicker": "hallo"},
                         {"layout": "photo", "photo": rel(1), "body": "sonstraal"},
                         {"layout": "polaroid", "photo": rel(2), "body": "wangetjies"},
                         {"layout": "collage", "photos": [rel(0), rel(1), rel(2)], "title": "ons is lief vir jou"}],
            "stories": [{"layout": "collage", "photos": [rel(0), rel(1)], "title": "Liara", "tag": "nuwe reel"},
                        {"layout": "polaroid", "photo": rel(2), "title": "kruip"}]})
        out = postkit.make(slug)
        assert len(out["carousel"]) == 4 and len(out["stories"]) == 2
        assert Image.open(project.path(slug, "posts", "carousel-01.png")).size == (1080, 1350)
        st = Image.open(project.path(slug, "posts", "story-01.png")).convert("RGB")
        assert st.size == (1080, 1920)
        # blush paper behind the prints, not the business brand colour
        r, g, b = st.getpixel((40, 1880))
        assert r > 200 and r >= b and abs(r - g) < 40
    finally:
        shutil.rmtree(project.path(slug), ignore_errors=True)
