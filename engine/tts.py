"""Offline text-to-speech using the Kokoro model + espeak-ng phonemes.

speak(sentences, voice) -> (audio float32 @24kHz, list of (start, end) seconds per sentence)
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import onnxruntime as rt

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "kokoro-v1.0.onnx"
VOICES = ROOT / "models" / "voices-v1.0.bin"
VOCAB = json.load(open(ROOT / "models" / "config.json"))["vocab"]
SR = 24000

_sess = None
_voices = None


def _load():
    global _sess, _voices
    if _sess is None:
        opts = rt.SessionOptions()
        _sess = rt.InferenceSession(str(MODEL), opts, providers=["CPUExecutionProvider"])
        _voices = np.load(VOICES)


def _espeak(text: str, lang: str) -> str:
    out = subprocess.run(
        ["espeak-ng", "-q", "--ipa", "-v", lang, text],
        capture_output=True, text=True, check=True,
    ).stdout
    return " ".join(out.split())


def phonemize(text: str, lang: str = "en-us") -> str:
    # keep punctuation (espeak drops it) by phonemizing the pieces between marks
    parts = re.split(r"([,.!?;:—–-]+)", text)
    res = []
    for p in parts:
        if not p.strip():
            continue
        if re.fullmatch(r"[,.!?;:—–-]+", p.strip()):
            mark = p.strip()[0]
            mark = "," if mark in "—–-;:" else mark
            res.append(mark)
        else:
            res.append(" " + _espeak(p.strip(), lang))
    ph = "".join(res).strip()
    return "".join(c for c in ph if c in VOCAB)


def _synth(phonemes: str, voice: str, speed: float) -> np.ndarray:
    tokens = [VOCAB[c] for c in phonemes][:510]
    style = _voices[voice][len(tokens)]
    audio = _sess.run(None, {
        "tokens": np.array([[0, *tokens, 0]], dtype=np.int64),
        "style": style.astype(np.float32),
        "speed": np.array([speed], dtype=np.float32),
    })[0]
    return np.asarray(audio, dtype=np.float32).ravel()


def _trim(a: np.ndarray, thr: float = 0.01) -> np.ndarray:
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a
    s = max(0, idx[0] - int(0.02 * SR))
    e = min(len(a), idx[-1] + int(0.05 * SR))
    return a[s:e]


def speak(sentences, voice="am_michael", speed=1.08, gap=0.18, lang="en-us"):
    _load()
    chunks, times, t = [], [], 0.25
    chunks.append(np.zeros(int(0.25 * SR), np.float32))
    for s in sentences:
        a = _trim(_synth(phonemize(s, lang), voice, speed))
        chunks.append(a)
        times.append((t, t + len(a) / SR))
        t += len(a) / SR
        pause = np.zeros(int(gap * SR), np.float32)
        chunks.append(pause)
        t += gap
    chunks.append(np.zeros(int(0.4 * SR), np.float32))
    audio = np.concatenate(chunks)
    audio = audio / max(1e-6, np.abs(audio).max()) * 0.9
    return audio, times
