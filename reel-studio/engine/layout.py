"""Layout: safe zones, placing things so they never collide, bubbles that fit text,
and user overlays (logos, photos, anything dropped into inbox/).
"""
import os
from PIL import Image
from . import stickers, textfit

W, H = 1080, 1920

# Instagram/TikTok UI covers these areas: keep text, logos and stickers out.
SAFE = dict(top=220, bottom=440, left=60, right=150)
SAFE_BOX = (SAFE["left"], SAFE["top"], W - SAFE["right"], H - SAFE["bottom"])


def overlaps(a, b, pad=20):
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


def inside_safe(r):
    return r[0] >= SAFE_BOX[0] and r[1] >= SAFE_BOX[1] and r[2] <= SAFE_BOX[2] and r[3] <= SAFE_BOX[3]


def free_spot(size, taken, near=None):
    """Find a spot for an item of `size` that's inside the safe zone and doesn't
    cover any rectangle in `taken` (text blocks, logo, other stickers)."""
    w, h = int(size[0]), int(size[1])
    cands = []
    for y in range(SAFE_BOX[1], SAFE_BOX[3] - h + 1, 20):
        for x in range(SAFE_BOX[0], SAFE_BOX[2] - w + 1, 20):
            r = (x, y, x + w, y + h)
            if not any(overlaps(r, t) for t in taken):
                cx, cy = x + w / 2, y + h / 2
                d = ((cx - near[0]) ** 2 + (cy - near[1]) ** 2) if near else 0
                cands.append((d, r))
    return min(cands)[1] if cands else None


def bubble_with_text(text, pack, width=640, font_role="accent", max_px=96, min_px=52):
    """Thought bubble whose text ALWAYS fits: fit text to the bubble's inner safe
    area; if it would drop below min_px, grow the bubble and try again."""
    font = pack["fonts"][font_role]
    for _ in range(8):
        height = int(width * 0.78)
        # inner text area = the calm middle of the cloud, away from the lobes
        box_w, box_h = width * 0.62, height * 0.40
        fit = textfit.fit_text(text, font["file"], box_w, box_h, max_px=max_px,
                               min_px=min_px, weight=font.get("weight"))
        if fit["fits"]:
            break
        width = int(width * 1.15)
    pen = stickers.Pen(pack, "accent", seed=len(text), style="doodle")
    svg = pen.svg(stickers.bubble_shape(pen, 200, 156), size=200)
    img = stickers.svg_to_img(svg, width)
    txt = textfit.render_block(fit, pack["colors"]["bubble_text"])
    # centre text on the cloud body (the cloud body sits at ~42% of the drawing)
    body_cy = img.height * (10 + 156 * 0.42) / 220
    img.alpha_composite(txt, (int((img.width - txt.width) / 2), int(body_cy - txt.height / 2)))
    return img


# ---------------------------------------------------------------- user overlays
POSITIONS = {
    "top-left": (0, 0), "top-center": (0.5, 0), "top-right": (1, 0),
    "center": (0.5, 0.5), "bottom-left": (0, 1), "bottom-center": (0.5, 1), "bottom-right": (1, 1),
}


def load_overlay(path, knock_out_white=False):
    """Load any logo/image the user dropped in: PNG, JPG, WEBP or SVG.
    knock_out_white makes a plain white background transparent (common for JPG logos)."""
    if path.lower().endswith(".svg"):
        img = stickers.svg_to_img(open(path).read(), 800)
    else:
        img = Image.open(path).convert("RGBA")
    if knock_out_white:
        px = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = px[x, y]
                if r > 240 and g > 240 and b > 240:
                    px[x, y] = (r, g, b, 0)
    return img


def place_overlay(img, position="top-right", width_frac=0.2, margin=24):
    """Scale an overlay and return (image, (x, y)) inside the safe zone."""
    w = int(W * width_frac)
    img = img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)
    fx, fy = POSITIONS[position]
    x0, y0, x1, y1 = SAFE_BOX
    x = int(x0 + margin + fx * (x1 - x0 - img.width - 2 * margin))
    y = int(y0 + margin + fy * (y1 - y0 - img.height - 2 * margin))
    return img, (x, y)


def inbox_files(root):
    """Everything the user dragged into inbox/ (their logo, product shots, extras)."""
    d = os.path.join(root, "inbox")
    exts = (".png", ".jpg", ".jpeg", ".webp", ".svg")
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(exts)) if os.path.isdir(d) else []


def _lum(rgb):
    r, g, b = [c / 255 for c in rgb[:3]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ensure_contrast(img, bg_hex, paper_hex, min_diff=0.35):
    """If a logo would disappear on the background (dark logo on dark bg, etc.),
    put it on a soft rounded 'paper' pill so it always reads."""
    from PIL import ImageDraw
    px = [p for p in img.getdata() if p[3] > 128]
    if not px:
        return img
    logo_l = sum(_lum(p) for p in px) / len(px)
    # also check the darkest/lightest 20% (logos often mix a colour mark + text)
    ls = sorted(_lum(p) for p in px)
    extremes = [ls[len(ls) // 10], ls[-len(ls) // 10 - 1]]
    bg_l = _lum(tuple(int(bg_hex[i:i + 2], 16) for i in (1, 3, 5)))
    if min(abs(bg_l - l) for l in extremes + [logo_l]) >= min_diff:
        return img
    pad = int(img.height * 0.25)
    pill = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2))
    ImageDraw.Draw(pill).rounded_rectangle((0, 0, pill.width - 1, pill.height - 1),
                                           radius=pill.height // 2, fill=paper_hex)
    pill.alpha_composite(img, (pad, pad))
    return pill
