"""Narrate a long-form script: writes <out>/voice.wav and <out>/timeline.json."""
import json, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine"))
import tts

spec = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
SR = tts.SR; tts._load()
voice, speed = spec.get("voice", "bm_george"), spec.get("speed", 0.94)
LINE_GAP, SCENE_GAP, CH_TITLE = 0.42, 0.9, 2.6
buf, t, timeline = [np.zeros(int(0.6*SR), np.float32)], 0.6, []
def add_sil(sec):
    global t
    buf.append(np.zeros(int(sec*SR), np.float32)); t += sec
for ci, ch in enumerate(spec["chapters"]):
    chap = {"name": ch["name"], "start": t, "scenes": []}
    if ci > 0: add_sil(CH_TITLE)          # chapter title card holds here
    for sc in ch["scenes"]:
        s = {**{k: v for k, v in sc.items() if k != "lines"}, "start": t, "lines": []}
        for ln in sc["lines"]:
            a = tts._trim(tts._synth(tts.phonemize(ln), voice, speed))
            s["lines"].append({"text": ln, "start": t, "end": t + len(a)/SR})
            buf.append(a); t += len(a)/SR; add_sil(LINE_GAP)
        add_sil(SCENE_GAP - LINE_GAP); s["end"] = t; chap["scenes"].append(s)
    chap["end"] = t; timeline.append(chap)
add_sil(2.5)
audio = np.concatenate(buf); audio = audio / np.abs(audio).max() * 0.89
wavfile.write(out / "voice.wav", SR, (audio*32767).astype(np.int16))
json.dump({"duration": t, "chapters": timeline}, open(out / "timeline.json", "w"), indent=1)
print("duration", round(t, 1))
