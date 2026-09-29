"""Local speech-to-text with word timings (faster-whisper). Runs on the user's computer,
so it costs no Claude usage. Results are cached next to the project.
"""
import json, os, subprocess, tempfile

MODEL_SIZE = os.environ.get("REEL_WHISPER_MODEL", "small")


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def has_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                          "stream=codec_type", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return "audio" in out


def transcribe(path, cache=None, language=None):
    """Returns {"language", "words": [{"w", "start", "end"}], "duration"}."""
    if cache and os.path.exists(cache):
        return json.load(open(cache))
    result = {"language": language, "words": [], "duration": probe_duration(path)}
    if has_audio(path):
        from faster_whisper import WhisperModel
        wav = os.path.join(tempfile.mkdtemp(), "a.wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-ac", "1", "-ar", "16000", wav], check=True)
        model = WhisperModel(MODEL_SIZE, device="auto", compute_type="int8")
        segs, info = model.transcribe(wav, language=language, word_timestamps=True, vad_filter=False,
                                      condition_on_previous_text=False)
        result["language"] = info.language
        for s in segs:
            for w in s.words or []:
                result["words"].append({"w": w.word.strip(), "start": round(w.start, 3),
                                        "end": round(w.end, 3), "p": round(w.probability, 3)})
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(result, open(cache, "w"), indent=1)
    return result
