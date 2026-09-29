"""Person cut-out masks for 'text behind you' (MediaPipe selfie segmenter, Apache 2.0).

The 250 KB model downloads once to library/models/. Runs locally, frame by frame, only
while a behind-the-person layer is on screen.
"""
import os, urllib.request
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/"
             "float16/latest/selfie_segmenter.tflite")
MODEL = os.path.join(ROOT, "library", "models", "selfie_segmenter.tflite")


class PersonMasker:
    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision
        if not os.path.exists(MODEL):
            os.makedirs(os.path.dirname(MODEL), exist_ok=True)
            urllib.request.urlretrieve(MODEL_URL, MODEL)
        opts = vision.ImageSegmenterOptions(base_options=mpt.BaseOptions(model_asset_path=MODEL),
                                            running_mode=vision.RunningMode.VIDEO,
                                            output_confidence_masks=True)
        self.mp = mp
        self.seg = vision.ImageSegmenter.create_from_options(opts)
        self.prev = None

    def mask(self, frame_rgba, t_ms):
        """Soft person mask (PIL 'L', same size as frame), temporally smoothed."""
        rgb = np.ascontiguousarray(np.asarray(frame_rgba.convert("RGB")))
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        res = self.seg.segment_for_video(img, int(t_ms))
        m = np.array(res.confidence_masks[0].numpy_view(), dtype=np.float32, copy=True)
        if m.ndim == 3:
            m = m[..., 0]
        if self.prev is not None and self.prev.shape == m.shape:
            m = 0.6 * m + 0.4 * self.prev  # reduce flicker
        self.prev = m
        m = np.clip((m - 0.35) / 0.3, 0, 1)  # firm edge, soft falloff
        out = Image.fromarray((m * 255).astype(np.uint8), "L")
        return out.filter(ImageFilter.GaussianBlur(1.2))

    def close(self):
        self.seg.close()


def head_top(video, src_time, width=1080, height=1920):
    """Y (in 1080x1920 reel space) of the top of the person's head at `src_time`,
    or None if nobody is found. Used to place behind-you titles at hairline height."""
    m = person_mask(video, src_time, width, height)
    if m is None:
        return None
    h, w = m.shape
    centre = m[:, int(w * 0.3):int(w * 0.7)] > 0.5
    rows = np.where(centre.mean(axis=1) > 0.08)[0]
    return float(rows[0]) * height / h if len(rows) else None


def head_box(video, src_time, width=1080, height=1920):
    """Box (x0, y0, x1, y1 in reel space) around the person's head at `src_time`, or None.
    Used so stickers never cover a face, even when the speaker isn't centred."""
    m = person_mask(video, src_time, width, height)
    if m is None:
        return None
    h, w = m.shape
    person = m > 0.5
    rows = np.where(person.mean(axis=1) > 0.02)[0]
    if len(rows) < 5:
        return None
    y0, y1 = rows[0], rows[-1]
    band_end = min(y0 + max(int((y1 - y0) * 0.3), int(h * 0.08)), y0 + int(h * 0.3))
    cols = np.where(person[y0:band_end].any(axis=0))[0]
    if not len(cols):
        return None
    sx, sy = width / w, height / h
    pad = 40
    return tuple(float(v) for v in (max(0, cols[0] * sx - pad), max(0, y0 * sy - pad),
            min(width, cols[-1] * sx + pad), min(height, band_end * sy + pad)))


def person_mask(video, src_time, width=1080, height=1920):
    """Person confidence mask (numpy, model resolution) for one frame, or None."""
    import subprocess, tempfile
    png = os.path.join(tempfile.mkdtemp(), "f.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(max(src_time, 0)), "-i", video, "-frames:v", "1",
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}", png])
    if not os.path.exists(png):
        return None
    try:
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision
        import mediapipe as mp
        if not os.path.exists(MODEL):
            os.makedirs(os.path.dirname(MODEL), exist_ok=True)
            urllib.request.urlretrieve(MODEL_URL, MODEL)
        seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=mpt.BaseOptions(model_asset_path=MODEL), output_confidence_masks=True))
        img = mp.Image.create_from_file(png)
        m = np.array(seg.segment(img).confidence_masks[0].numpy_view(), copy=True)
        seg.close()
    except Exception:
        return None
    m = np.asarray(m)
    return m[..., 0] if m.ndim == 3 else m


FACE_URL = ("https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/"
            "float16/latest/blaze_face_short_range.tflite")
FACE_MODEL = os.path.join(ROOT, "library", "models", "blaze_face_short_range.tflite")
_face_det = None


def face_boxes(video, src_time, width=1080, height=1920, min_conf=0.55):
    """Faces in the frame at src_time: [(x0, y0, x1, y1, confidence)] in reel space, biggest first.
    On-device (MediaPipe BlazeFace, Apache 2.0, ~230 KB, downloaded once)."""
    global _face_det
    import subprocess, tempfile
    png = os.path.join(tempfile.mkdtemp(), "f.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(max(src_time, 0)), "-i", video, "-frames:v", "1",
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}", png])
    if not os.path.exists(png):
        return []
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mpt
        from mediapipe.tasks.python import vision
        if _face_det is None:
            if not os.path.exists(FACE_MODEL):
                os.makedirs(os.path.dirname(FACE_MODEL), exist_ok=True)
                urllib.request.urlretrieve(FACE_URL, FACE_MODEL)
            _face_det = vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
                base_options=mpt.BaseOptions(model_asset_path=FACE_MODEL), min_detection_confidence=min_conf))
        frame = np.asarray(Image.open(png).convert("RGB"))

        def detect(arr, ox=0, oy=0, k=1.0):
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(arr))
            found = []
            for d in _face_det.detect(img).detections:
                b = d.bounding_box
                found.append((ox + b.origin_x / k, oy + b.origin_y / k, ox + (b.origin_x + b.width) / k,
                              oy + (b.origin_y + b.height) / k, float(d.categories[0].score)))
            return found

        out = detect(frame)
        if not out:  # small faces (wide shots): look again in zoomed tiles of the upper 2/3
            tw, th = width // 2, height // 3
            for oy in (0, th // 2, th):
                for ox in (0, tw // 2, tw):
                    tile = Image.fromarray(frame[oy:oy + th, ox:ox + tw]).resize((tw * 2, th * 2))
                    out += detect(np.asarray(tile), ox, oy, 2.0)
            out = _dedupe(out)
    except Exception:
        return []
    return sorted([tuple(float(v) for v in f) for f in out], key=lambda f: -(f[2] - f[0]) * (f[3] - f[1]))


def _dedupe(boxes):
    keep = []
    for b in sorted(boxes, key=lambda f: -f[4]):
        if all(min(b[2], k[2]) - max(b[0], k[0]) <= 0 or min(b[3], k[3]) - max(b[1], k[1]) <= 0 for k in keep):
            keep.append(b)
    return keep
