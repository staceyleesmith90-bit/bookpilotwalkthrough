from engine import roughcut, sayit


def _t(text, gap=0.35):
    ws, t = [], 0.5
    for w in text.split():
        ws.append({"w": w, "start": round(t, 2), "end": round(t + 0.3, 2)})
        t += gap
    return {"words": ws, "duration": t + 1}


def test_cue_words_are_cut_and_the_next_line_gets_the_effect():
    rc = roughcut.rough_cut(_t("Hello there everyone. Cue zoom. This is the part nobody tells you. Queue b-roll. We pack every order by hand."))
    said = " ".join(l["text"] for l in rc["lines"] if l["keep"]).lower()
    assert "cue" not in said and "queue" not in said and "b-roll" not in said
    by = {l["text"].split()[0]: l for l in rc["lines"]}
    assert by["This"]["cues"] == ["zoom"]
    assert by["We"]["cues"] == ["broll"]
    assert sayit.dos(by["This"]) == ["zoom:punch"]


def test_scratch_that_drops_the_line_before():
    rc = roughcut.rough_cut(_t("I started in twenty nineteen. Scratch that. I started my shop in twenty eighteen."))
    kept = [l["text"] for l in rc["lines"] if l["keep"]]
    assert kept == ["I started my shop in twenty eighteen."]


def test_normal_speech_is_left_alone():
    words, cues = sayit.extract(_t("we cut that in half and added a cute sticker")["words"])
    assert cues == [] and len(words) == 10
