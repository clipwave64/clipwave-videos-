"""Original ClipWave presenter: Dr. Swordfish, a cartoon swordfish in a white doctor's coat.
Drawn entirely in code. Mouth follows the voice, eyes blink, fin gestures, coat and tail sway."""
import math
import random

import numpy as np
from PIL import Image, ImageDraw

SS = 2          # supersampling
CW, CH = 1000, 680
INK = (22, 34, 66)
BLUE = (46, 118, 214)
BLUE_D = (28, 84, 170)
BELLY = (214, 232, 244)
COAT = (250, 252, 255)
COAT_S = (205, 216, 232)
SCRUB = (44, 190, 170)
RED = (232, 62, 76)
STEEL = (70, 80, 104)


def _h(x):
    u = max(0.0, min(1.0, (x - 120) / 590))
    return 158 * math.sin(math.pi * u ** 0.78) ** 0.8 + 12


CY = 350


def _p(pts):
    return [(x * SS, y * SS) for x, y in pts]


def _poly(d, pts, fill, w=6):
    d.polygon(_p(pts), fill=fill)
    d.line(_p(pts + pts[:1]), fill=INK, width=w * SS, joint="curve")


def _rot(pts, c, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + (x - c[0]) * ca - (y - c[1]) * sa, c[1] + (x - c[0]) * sa + (y - c[1]) * ca) for x, y in pts]


def _circ(d, x, y, r, fill, w=0):
    d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=fill,
              outline=INK if w else None, width=w * SS)


class Character:
    def __init__(self, voice, sr, fps, scene_times, seed="clipwave"):
        hop = sr / fps
        n = int(len(voice) / hop) + 2
        rms = [0.0] * n
        for i in range(n):
            s = voice[int(i * hop):int((i + 1) * hop)]
            rms[i] = float((s ** 2).mean()) ** 0.5 if len(s) else 0.0
        peak = sorted(rms)[int(n * 0.95)] or 1.0
        env = np.minimum(1.0, np.array(rms) / peak)
        kernel = np.exp(-0.5 * (np.arange(-9, 10) / 3.5) ** 2)
        self.level = np.convolve(env, kernel / kernel.sum(), mode="same").tolist()
        self.fps = fps
        self.times = scene_times
        r = random.Random(seed)
        self.blinks, t = [], 1.2
        while t < n / fps:
            self.blinks.append(t)
            t += r.uniform(3.5, 6.5)
        self.cache = {}

    def _build(self, mouth, blink, pose, look):
        """all continuous: mouth 0..1, blink 0..1, pose -1..1, look -1..1"""
        im = Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        sw = pose
        # tail
        tc = (135, CY)
        _poly(d, _rot([(150, CY - 14), (40, CY - 145), (82, CY), (40, CY + 145), (150, CY + 14)], tc, sw * 11), BLUE_D)
        # coat flap flaring behind the body
        hc = (228, 430)
        _poly(d, _rot([(243, 395), (148, 520), (133, 600), (205, 575), (243, 612), (295, 572), (343, 505)], hc, sw * 6), COAT)
        # dorsal fin and lower fin
        _poly(d, [(300, 215), (345, 62), (395, 60), (445, 205)], BLUE_D)
        _poly(d, [(505, 480), (535, 565), (470, 515)], BLUE_D)
        # bill
        _poly(d, [(650, 296), (985, 262), (992, 274), (664, 362)], (60, 136, 226))
        # body
        xs = list(range(120, 711, 10))
        up = [(x, CY - _h(x)) for x in xs]
        lo = [(x, CY + _h(x)) for x in reversed(xs)]
        _poly(d, up + lo, BELLY)
        band = [(x, CY + 26 * math.sin((x - 120) / 590 * math.pi) - 22) for x in reversed(xs)]
        d.polygon(_p(up + band), fill=BLUE)
        # coat over the middle of the body
        cx = list(range(205, 439, 8))
        cu = [(x, CY - _h(x) - 10) for x in cx]
        cl = [(x, CY + _h(x) + 12) for x in reversed(cx)]
        _poly(d, cu + cl, COAT)
        d.line(_p([(218, CY - 95), (218, CY + 125)]), fill=COAT_S, width=7 * SS)
        # scrubs and lapels at the front of the coat
        top, bot = CY - _h(413) - 9, CY + _h(413) + 11
        _poly(d, [(395, top), (437, top + 2), (437, bot - 2), (395, bot)], SCRUB, 5)
        _poly(d, [(395, top), (345, top + 16), (381, CY - 28), (405, CY - 2)], COAT, 5)
        _poly(d, [(437, top + 2), (459, CY - 92), (429, CY - 22), (405, CY - 2)], COAT, 5)
        for y in (CY + 26, CY + 82, CY + 134):
            _circ(d, 381, y, 8, COAT_S, 3)
        # pocket, pen, red cross
        d.rounded_rectangle([262 * SS, 402 * SS, 338 * SS, 470 * SS], radius=8 * SS, fill=COAT, outline=INK, width=4 * SS)
        d.rounded_rectangle([312 * SS, 372 * SS, 324 * SS, 412 * SS], radius=5 * SS, fill=RED, outline=INK, width=3 * SS)
        d.rectangle([288 * SS, 278 * SS, 302 * SS, 324 * SS], fill=RED)
        d.rectangle([272 * SS, 294 * SS, 318 * SS, 308 * SS], fill=RED)
        # stethoscope
        d.line(_p([(413, top + 8), (367, CY - 42), (343, CY + 30), (347, CY + 92)]), fill=STEEL, width=9 * SS, joint="curve")
        _circ(d, 347, CY + 108, 21, (184, 196, 214), 5)
        _circ(d, 347, CY + 108, 8, STEEL)
        # arm: coat sleeve ending in a fin, gesturing with the speech
        sh = (405, 430)
        ang = -14 + sw * 22
        _poly(d, _rot([(395, 410), (492, 438), (525, 476), (488, 498), (387, 468)], sh, ang), BLUE_D)
        _poly(d, _rot([(387, 404), (470, 428), (456, 486), (375, 468)], sh, ang), COAT)
        # eye
        ex, ey = 560, 305
        open_ = 1 - blink
        sy = max(3, 40 * open_)
        d.ellipse([(ex - 40) * SS, (ey - sy) * SS, (ex + 40) * SS, (ey + sy) * SS], fill=(255, 255, 255), outline=INK, width=6 * SS)
        if open_ > 0.2:
            px, pr = ex + 12 + look * 9, min(22, sy * 0.6)
            _circ(d, px, ey + 3, pr, (18, 22, 48))
            _circ(d, px + 7, ey - 6 * open_, max(1, 6 * open_), (255, 255, 255))
        # brow
        d.line(_p([(ex - 36, ey - 54 - mouth * 3), (ex + 34, ey - 60 - mouth * 5)]), fill=INK, width=10 * SS)
        # mouth
        mx, my, mw = 592, 392, 48
        o = 3 + mouth * 34
        d.ellipse([(mx - mw + 8) * SS, (my - o * 0.45) * SS, (mx + mw - 18) * SS, (my + o) * SS],
                  fill=(116, 24, 52), outline=INK, width=7 * SS)
        if o > 12:
            k = min(1.0, (o - 12) / 14)
            d.ellipse([(mx - 18 * k) * SS, (my + o * 0.2) * SS, (mx + 14 * k) * SS, (my + o - 5) * SS], fill=(236, 92, 118))
        return im.resize((CW, CH), Image.LANCZOS)

    def draw(self, frame, t, cx=480, top=235):
        i = min(int(t * self.fps), len(self.level) - 1)
        mouth = round(min(1.0, self.level[i] * 0.85) * 16) / 16
        blink = 0.0
        for b in self.blinks:
            if 0 <= t - b < 0.45:  # eyelid eases shut and open over 0.45 s
                blink = max(blink, math.sin((t - b) / 0.45 * math.pi) ** 2)
        blink = round(blink * 10) / 10
        pose = round(math.sin(t * 0.9) * 40) / 40    # slow, constant-speed sway
        look = round(math.sin(t * 0.35) * 8) / 8
        key = (mouth, blink, pose, look)
        if key not in self.cache:
            if len(self.cache) > 300:
                self.cache.clear()
            self.cache[key] = self._build(*key)
        tilt = math.sin(t * 0.7) * 1.2
        y = math.sin(t * 0.9) * 9
        # sub-pixel placement so slow drift glides instead of stepping
        rot = self.cache[key].rotate(tilt, resample=Image.BICUBIC, center=(450, 350), translate=(0, y))
        frame.alpha_composite(rot, (int(cx - CW / 2), top))
