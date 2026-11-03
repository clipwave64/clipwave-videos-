"""Mix narration with a soft, original synthesized ambient pad -> mix.wav"""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
work = sys.argv[1]
sr, v = wavfile.read(f"{work}/voice.wav")
v = v.astype(np.float32) / 32768
n = len(v); t = np.arange(n) / sr
pad = np.zeros(n, np.float32)
chords = [[110.0, 164.81, 220.0, 261.63], [98.0, 146.83, 196.0, 246.94], [87.31, 130.81, 174.61, 220.0], [98.0, 146.83, 196.0, 293.66]]
seg = 16.0
for i, ch in enumerate(chords * int(n / sr / seg / 4 + 2)):
    s0 = int(i * seg * sr); s1 = min(n, int((i + 1) * seg * sr + 4 * sr))
    if s0 >= n: break
    tt = np.arange(s1 - s0) / sr
    env = np.clip(tt / 4, 0, 1) * np.clip((s1 - s0) / sr - tt, 0, 4) / 4
    for f in ch:
        for det in (-0.6, 0.6):
            pad[s0:s1] += (np.sin(2 * np.pi * (f + det) * tt) * env).astype(np.float32) * 0.5
pad = sosfilt(butter(2, 900, fs=sr, output="sos"), pad).astype(np.float32)
pad *= (0.85 + 0.15 * np.sin(2 * np.pi * t / 23)).astype(np.float32)
pad = pad / np.abs(pad).max() * 0.07
fade = np.clip(t / 3, 0, 1) * np.clip((t[-1] - t) / 4, 0, 1)
mix = v + pad * fade.astype(np.float32)
mix = mix / np.abs(mix).max() * 0.92
wavfile.write(f"{work}/mix.wav", sr, (mix * 32767).astype(np.int16))
print("ok")
