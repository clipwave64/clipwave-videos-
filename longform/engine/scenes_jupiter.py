"""Scene library for the Jupiter long-form video. Every visual is generated in code (no downloaded footage)."""
import math
import numpy as np
import cv2
import gfx
from gfx import W, H, Sphere, texture, space_bg, add_layer, glow, smoothstep, fbm, ramp
from scenes import ease, camera, draw_probe, TAU

JUP_ATM = (235, 200, 160)      # RGB rim colour
SPOT_U, SPOT_LAT = 0.6, -22.0  # Great Red Spot position on the texture

_tex = {}


def _store(name, t):
    t = np.clip(t, 0, 255).astype(np.uint8)[..., ::-1].copy()
    _tex[name] = t
    return t


def jup_tex(spots=0):
    """Procedural banded Jupiter map (BGR) with the Great Red Spot. spots = number of dark impact scars."""
    key = f"jup{spots}"
    if key in _tex:
        return _tex[key]
    th, tw = 1024, 2048
    v = np.linspace(0, 1, th, dtype=np.float32)[:, None]
    u = np.linspace(0, 1, tw, dtype=np.float32)[None, :]
    lat = (0.5 - v) * 180.0
    turb = fbm(th, tw, 2.4, 301, ax=6.0, ay=1.0)
    fine = fbm(th, tw, 1.7, 302, ax=8.0, ay=1.0)
    latw = lat + 3.0 * (turb - 0.5) + 1.2 * np.sin(u * TAU * 9 + lat * 0.3)
    # alternating zones (pale) and belts (dark), narrower toward the poles
    band = 0.5 + 0.38 * np.cos(np.radians(latw) * 13.0) + 0.12 * np.cos(np.radians(latw) * 37.0 + 1.0)
    band = np.clip((band - 0.5) * 1.6 + 0.5, 0, 1)
    x = 0.62 * band + 0.25 * fine + 0.13 * turb
    t = ramp(x, [(0, (120, 78, 52)), (0.3, (168, 116, 78)), (0.55, (205, 168, 128)), (0.78, (232, 214, 186)), (1, (246, 238, 222))])
    # warm equatorial tint and grey-blue poles
    eq = smoothstep(18, 4, np.abs(lat))
    t = t * (1 - 0.25 * eq[..., None]) + np.array([225, 175, 120], np.float32) * 0.25 * eq[..., None]
    pole = smoothstep(55, 80, np.abs(latw))
    t = t * (1 - 0.6 * pole[..., None]) + np.array([150, 140, 135], np.float32) * 0.6 * pole[..., None]
    # Great Red Spot: an oval with a swirl
    du = (u - SPOT_U) * 2.0 * 180 / 1.0   # degrees of longitude
    dl = lat - SPOT_LAT
    rr = np.sqrt((du / 11.0) ** 2 + (dl / 6.5) ** 2)
    ang = np.arctan2(dl / 6.5, du / 11.0)
    swirl = 0.5 + 0.5 * np.sin(ang * 2 + rr * 9 + 2 * fine)
    core = smoothstep(1.0, 0.75, rr)
    spot_col = ramp(swirl * 0.6 + 0.4 * (1 - rr), [(0, (170, 80, 50)), (0.5, (200, 100, 60)), (1, (225, 140, 95))])
    t = t * (1 - core[..., None]) + spot_col * core[..., None]
    collar = smoothstep(1.35, 1.0, rr) * (1 - core)
    t = t * (1 - 0.55 * collar[..., None]) + np.array([240, 228, 205], np.float32) * 0.55 * collar[..., None]
    # a few white ovals
    r = np.random.default_rng(303)
    for _ in range(14):
        cu, cl = r.uniform(0, 1), r.choice([-40, -33, 28, 35, 41]) + r.uniform(-1.5, 1.5)
        d = np.sqrt(((u - cu) * 360 / 3.0) ** 2 + ((lat - cl) / 1.6) ** 2)
        o = smoothstep(1.0, 0.4, d)
        t = t * (1 - 0.8 * o[..., None]) + np.array([248, 242, 232], np.float32) * 0.8 * o[..., None]
    # Shoemaker-Levy 9 style dark scars (southern latitudes)
    for k in range(spots):
        cu = 0.18 + 0.075 * k
        d = np.sqrt(((u - cu) * 360 / 4.5) ** 2 + ((lat + 44) / 3.2) ** 2)
        o = smoothstep(1.0, 0.25, d)
        t = t * (1 - 0.85 * o[..., None]) + np.array([45, 30, 28], np.float32) * 0.85 * o[..., None]
    t = cv2.GaussianBlur(t, (0, 0), 0.8)
    return _store(key, t)


def moon_tex(name):
    if name in _tex:
        return _tex[name]
    th, tw = 1024, 2048
    a = fbm(th, tw, 2.1, 311 + len(name))
    b = fbm(th, tw, 1.6, 321 + len(name))
    r = np.random.default_rng(331 + len(name))
    if name == "io":
        t = ramp(0.7 * a + 0.3 * b, [(0, (170, 120, 40)), (0.45, (215, 185, 80)), (0.7, (235, 220, 130)), (1, (245, 240, 200))])
        img = t.copy()
        for _ in range(90):
            cx, cy, rad = int(r.uniform(0, tw)), int(r.uniform(120, th - 120)), int(r.uniform(4, 16))
            col = [(40, 25, 15), (190, 70, 30), (120, 60, 30)][r.integers(0, 3)]
            cv2.circle(img, (cx, cy), rad, col, -1, cv2.LINE_AA)
            if r.random() < 0.4:
                cv2.circle(img, (cx, cy), rad * 3, (200, 110, 50), 2, cv2.LINE_AA)
        t = cv2.GaussianBlur(img, (0, 0), 1.5)
    elif name == "europa":
        t = ramp(0.6 * a + 0.4 * b, [(0, (190, 175, 150)), (0.5, (225, 215, 195)), (1, (248, 245, 238))])
        img = t.copy()
        for _ in range(140):
            x0, y0 = r.uniform(0, tw), r.uniform(100, th - 100)
            ang, L = r.uniform(0, math.pi), r.uniform(80, 600)
            pts = []
            for s in np.linspace(0, 1, 30):
                pts.append((x0 + math.cos(ang) * L * s + 18 * math.sin(s * 7 + x0), y0 + math.sin(ang) * L * s * 0.5))
            cv2.polylines(img, [np.array(pts, np.int32)], False, (150, 95, 60), int(r.integers(1, 4)), cv2.LINE_AA)
        t = cv2.GaussianBlur(img, (0, 0), 1.0)
    elif name == "ganymede":
        light = smoothstep(0.5, 0.62, fbm(th, tw, 2.3, 341))
        t = ramp(a, [(0, (75, 65, 55)), (1, (130, 118, 102))])
        t = t * (1 - light[..., None]) + ramp(b, [(0, (165, 158, 148)), (1, (215, 210, 200))]) * light[..., None]
        img = t.copy()
        for _ in range(160):
            cx, cy, rad = int(r.uniform(0, tw)), int(r.uniform(60, th - 60)), int(r.uniform(2, 9))
            cv2.circle(img, (cx, cy), rad, (235, 232, 228), -1, cv2.LINE_AA)
        t = cv2.GaussianBlur(img, (0, 0), 1.2)
    elif name == "callisto":
        t = ramp(a, [(0, (40, 34, 28)), (1, (100, 88, 72))])
        img = t.copy()
        for _ in range(700):
            cx, cy, rad = int(r.uniform(0, tw)), int(r.uniform(30, th - 30)), int(r.uniform(1, 7) ** 1.2)
            cv2.circle(img, (cx, cy), rad, (200, 195, 185), -1, cv2.LINE_AA)
        cv2.circle(img, (int(tw * 0.3), int(th * 0.45)), 90, (150, 140, 125), 6, cv2.LINE_AA)
        cv2.circle(img, (int(tw * 0.3), int(th * 0.45)), 150, (130, 120, 105), 4, cv2.LINE_AA)
        t = cv2.GaussianBlur(img, (0, 0), 1.0)
    else:
        raise KeyError(name)
    return _store(name, t)


# ------------------------------------------------------------------ scenes
class JupiterCloseup:
    """Variants: 0 intro approach, 1 side-lit drift, 2 huge limb view, 3+ slow spin."""

    def __init__(self, dur, variant=0, **_):
        self.v = variant % 4
        if self.v == 2:
            self.sph = Sphere(820, light=(-0.75, 0.45, 0.5), incl=0.25, atm=JUP_ATM, atm_k=0.5)
        elif self.v == 1:
            self.sph = Sphere(440, light=(0.7, 0.2, 0.68), incl=0.1, atm=JUP_ATM, atm_k=0.5)
        else:
            self.sph = Sphere(470, light=(-0.55, 0.3, 0.78), incl=0.12, atm=JUP_ATM, atm_k=0.5)

    def frame(self, t, p):
        f = space_bg(t, (4, 1.5))
        tex = jup_tex()
        if self.v == 0:
            sc = 0.32 + 0.73 * ease(min(1, p * 1.25))
            self.sph.composite(f, 1060 + 120 * (1 - sc), 540, tex, 0.45 + t * 0.004, scale=sc)
            return camera(f, 1 + 0.03 * p)
        if self.v == 1:
            self.sph.composite(f, 760, 560, tex, 0.2 + t * 0.004)
            return camera(f, 1.0 + 0.08 * p, -30 * p, 0)
        if self.v == 2:
            self.sph.composite(f, 1300, 1250, tex, 0.1 + t * 0.006)
            return camera(f, 1.0 + 0.05 * p)
        self.sph.composite(f, 960, 560, tex, 0.5 + t * 0.005)
        return camera(f, 1.0 + 0.05 * p)


class JupiterScale:
    def __init__(self, dur, **_):
        self.j = Sphere(360, light=(-0.4, 0.25, 0.88), incl=0.1, atm=JUP_ATM, atm_k=0.5)
        self.e = Sphere(33, light=(-0.4, 0.25, 0.88), atm=(130, 180, 255), atm_k=1.2)

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.j.composite(f, 760, 440, jup_tex(), 0.55 + t * 0.005)
        self.e.composite(f, 1560, 480, texture("earth"), 0.3 + t * 0.01)
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [("JUPITER", 760, 835), ("EARTH", 1560, 560)]


class JupiterOrbits:
    def __init__(self, dur, **_):
        self.S, self.tilt = 165, 0.36
        self.tex = {"earth": texture("earth"), "jupiter": jup_tex()}
        self.planets = [("earth", 1.0, 365.25, 14, 0.4), ("jupiter", 5.2, 4333.0, 34, 2.2)]
        self.days_per_sec = (4333 * 1.02) / max(dur, 1)

    def proj(self, x, y):
        return 960 + x * self.S, 520 + y * self.S * self.tilt

    def frame(self, t, p):
        f = (space_bg(t, (1, 0)) * 0.7).astype(np.uint8)
        ov = np.zeros_like(f)
        th = np.linspace(0, TAU, 360)
        for name, a, per, r, ph in self.planets:
            pts = np.array([self.proj(a * math.cos(q), a * math.sin(q)) for q in th], np.int32)
            col = (110, 170, 230) if name == "jupiter" else (170, 170, 170)
            cv2.polylines(ov, [pts], True, col, 2, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.5, 0)
        days = t * self.days_per_sec
        bodies = [(0.0, "sun", 0, 0)]
        for name, a, per, r, ph in self.planets:
            q = ph + TAU * days / per
            bodies.append((a * math.sin(q), name, a * math.cos(q), r))
        self._pos = []
        for y, name, x, r in sorted(bodies):
            if name == "sun":
                glow(f, 960, 520, 40, (110, 200, 255), 1.0)
                cv2.circle(f, (960, 520), 20, (225, 250, 255), -1, cv2.LINE_AA)
                continue
            sx, sy = self.proj(x, y)
            L = np.array([960 - sx, sy - 520, 30.0]); n = np.linalg.norm(L)
            Sphere(r, light=(L[0] / n, L[1] / n, max(L[2] / n, 0.15)), halo=0.25, atm_k=0.8,
                   atm=(150, 200, 255) if name == "earth" else JUP_ATM).composite(f, sx, sy, self.tex[name], t * 0.05)
            self._pos.append((name.capitalize(), int(sx), int(sy + r + 24)))
        return camera(f, 1.03 - 0.03 * p)

    def labels(self, t):
        return getattr(self, "_pos", [])

    def hud(self, t, p):
        return f"{min(11.9, t * self.days_per_sec / 365.25):.1f} Earth years"


class JupiterBands:
    """Flat close-up of the cloud bands, each band drifting at its own speed and direction."""

    def __init__(self, dur, **_):
        tex = jup_tex()
        th, tw = tex.shape[:2]
        self.tex = tex
        ys = np.arange(H, dtype=np.float32)
        self.v = (0.30 + ys / H * 0.26) * th
        lat = (0.5 - self.v / th) * 180
        self.speed = (np.cos(np.radians(lat) * 13.0) * 38 + 12).astype(np.float32)   # px/s in texture units
        self.xs = np.arange(W, dtype=np.float32)

    def frame(self, t, p):
        th, tw = self.tex.shape[:2]
        mu = (self.xs[None, :] * 0.9 + 600 + self.speed[:, None] * t) % tw
        mv = np.broadcast_to(self.v[:, None], (H, W))
        img = cv2.remap(self.tex, mu.astype(np.float32), mv.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        g = np.linspace(-1, 1, W, dtype=np.float32)[None, :, None]
        img = (img.astype(np.float32) * (1.05 - 0.25 * g * g)).clip(0, 255).astype(np.uint8)
        return camera(img, 1.02 + 0.03 * p)


def _jup_sea():
    sea = gfx.CloudSea(seed=350)
    n = fbm(1024, 1024, 2.2, 351, ax=3.0)
    n2 = fbm(1024, 1024, 1.6, 352)
    x = 0.7 * n + 0.3 * n2
    sea.tex = ramp(x, [(0, (120, 75, 45)), (0.45, (190, 140, 95)), (0.7, (230, 200, 160)), (1, (248, 235, 215))])[..., ::-1].astype(np.float32).copy()
    return sea


class JupiterDive:
    """Flying low over the cloud tops, with lightning flashing deep below."""

    def __init__(self, dur, **_):
        self.sea = _jup_sea()
        r = np.random.default_rng(360)
        self.flashes = [(r.uniform(1, max(2, dur - 1)), r.uniform(200, 1700), r.uniform(560, 900)) for _ in range(int(dur / 2.2) + 2)]

    def frame(self, t, p):
        img = self.sea.render(t, horizon=0.4, speed=7.0, sky_top=(60, 60, 70), sky_hor=(150, 165, 185))
        for ft, x, y in self.flashes:
            d = t - ft
            if 0 <= d < 0.35:
                k = (1 - d / 0.35) * (0.6 + 0.4 * math.sin(d * 60))
                glow(img, x, y, 110, (255, 230, 200), 0.9 * k)
        return camera(img, 1.0 + 0.04 * p)


class JupiterSpot:
    def __init__(self, dur, **_):
        self.sph = Sphere(520, light=(-0.35, 0.25, 0.9), incl=0.0, atm=JUP_ATM, atm_k=0.5)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cy = 540
        self.sph.composite(f, 960, cy, jup_tex(), SPOT_U + 0.04 - 0.05 * ease(p))
        sy = 520 * math.sin(math.radians(-SPOT_LAT))
        z = 1.0 + 1.3 * ease(p)
        return camera(f, z, 0, -sy * (z - 1) * 0.9)


class JupiterPoles:
    """Top-down polar view: a central cyclone ringed by eight more."""

    def __init__(self, dur, **_):
        s = 1000
        n = fbm(s, s, 2.2, 370)
        self.base = ramp(n, [(0, (70, 75, 90)), (0.5, (120, 120, 130)), (1, (185, 175, 170))])[..., ::-1].astype(np.float32).copy()
        ys, xs = np.mgrid[0:s, 0:s].astype(np.float32)
        self.d = np.sqrt((xs - s / 2) ** 2 + (ys - s / 2) ** 2) / (s / 2)
        self.s = s
        self.centers = [(0, 0)] + [(0.42 * math.cos(k * TAU / 8), 0.42 * math.sin(k * TAU / 8)) for k in range(8)]

    def frame(self, t, p):
        s = self.s
        img = self.base.copy()
        for i, (cx, cy) in enumerate(self.centers):
            px, py = s / 2 + cx * s / 2, s / 2 + cy * s / 2
            R = 85 if i else 105
            for arm in range(3):
                pts = []
                for k in np.linspace(0, 1, 60):
                    a = arm * TAU / 3 + k * 4.5 + t * (0.35 if i else 0.25)
                    rr = R * k
                    pts.append((px + rr * math.cos(a), py + rr * math.sin(a)))
                cv2.polylines(img, [np.array(pts, np.int32)], False, (235, 230, 225), 7, cv2.LINE_AA)
            cv2.circle(img, (int(px), int(py)), 12, (60, 60, 70), -1, cv2.LINE_AA)
        img = cv2.GaussianBlur(img, (0, 0), 3.5)
        img *= (smoothstep(1.0, 0.92, self.d) * (0.6 + 0.4 * (1 - self.d)))[..., None]
        disc = np.clip(img, 0, 255).astype(np.uint8)
        f = space_bg(t, (2, 0))
        a = smoothstep(1.0, 0.98, self.d).astype(np.float32)
        M = cv2.getRotationMatrix2D((s / 2, s / 2), -t * 2.0, 0.9)
        disc = cv2.warpAffine(disc, M, (s, s))
        a = cv2.warpAffine(a, M, (s, s))[..., None]
        x0, y0 = 960 - s // 2, 520 - s // 2
        reg = f[y0:y0 + s, x0:x0 + s].astype(np.float32)
        f[y0:y0 + s, x0:x0 + s] = np.clip(reg * (1 - a) + disc * a, 0, 255).astype(np.uint8)
        return camera(f, 1.0 + 0.06 * p)

    def hud(self, t, p):
        return "North pole (artist's view)"


class JupiterInterior:
    LAYERS = [(1.00, (205, 160, 115), "Clouds"), (0.93, (175, 120, 85), "Hydrogen gas turning liquid"),
              (0.72, (110, 70, 95), "Metallic hydrogen"), (0.40, (70, 55, 120), "Fuzzy core")]

    def __init__(self, dur, **_):
        self.R = 430

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 720, 520
        R = self.R
        ov = f.copy()
        for k, (fr, col, _) in enumerate(self.LAYERS):
            rr = int(R * fr)
            cv2.circle(ov, (cx, cy), rr, col[::-1], -1, cv2.LINE_AA)
        # fuzzy core edge
        core = np.zeros_like(f, np.float32)
        cv2.circle(core, (cx, cy), int(R * 0.40), (150, 90, 70), -1, cv2.LINE_AA)
        core = cv2.GaussianBlur(core, (0, 0), 30)
        ov = np.clip(ov.astype(np.float32) * 0.85 + core * 0.4, 0, 255).astype(np.uint8)
        glow(ov, cx, cy, 70 + 6 * math.sin(t), (120, 160, 255), 0.35)
        # metallic shimmer
        pulse = 0.5 + 0.5 * math.sin(t * 1.5)
        cv2.circle(ov, (cx, cy), int(R * 0.72), (230, 160, 200), 2, cv2.LINE_AA)
        f = cv2.addWeighted(f, 0.0, ov, 1.0, 0)
        cv2.circle(f, (cx, cy), int(R * 0.72) - 4, (int(150 + 80 * pulse), 120, 180), 1, cv2.LINE_AA)
        self._cx, self._cy = cx, cy
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        out = []
        ys = [150, 300, 470, 640]
        for (fr, col, name), y in zip(self.LAYERS, ys):
            out.append((name, 1500, y))
        return out


class JupiterMagneto:
    def __init__(self, dur, **_):
        self.sph = Sphere(90, light=(-1, 0.1, 0.4), incl=0.1, atm=JUP_ATM, atm_k=0.4)
        r = np.random.default_rng(380)
        self.lines = []
        for L in (1.6, 2.4, 3.4, 4.6, 6.0):
            for side in (-1, 1):
                pts = []
                for th in np.linspace(0.15, math.pi - 0.15, 120):
                    rr = L * math.sin(th) ** 2
                    x = rr * math.sin(th) * side
                    y = rr * math.cos(th)
                    if side > 0:          # night side is stretched into a tail
                        x *= 1 + 0.25 * L * math.sin(th) ** 4
                    pts.append((x, y))
                self.lines.append(np.array(pts, np.float32))
        self.parts = [(r.integers(0, len(self.lines)), r.uniform(0, 1), r.uniform(0.05, 0.12)) for _ in range(160)]

    def frame(self, t, p):
        f = space_bg(t, (1, 0))
        cx, cy, S = 640, 540, 88
        glow(f, -200, 540, 260, (110, 200, 255), 0.6)
        ov = np.zeros_like(f)
        for ln in self.lines:
            pts = np.c_[cx + ln[:, 0] * S, cy - ln[:, 1] * S].astype(np.int32)
            cv2.polylines(ov, [pts], False, (255, 170, 110), 2, cv2.LINE_AA)
        for li, ph, sp in self.parts:
            ln = self.lines[li]
            k = (ph + t * sp) % 1
            i = int(k * (len(ln) - 1))
            cv2.circle(ov, (int(cx + ln[i, 0] * S), int(cy - ln[i, 1] * S)), 3, (255, 240, 200), -1, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.55 + 0.25 * smoothstep(0, 0.3, np.float32(p)).item(), 0)
        self.sph.composite(f, cx, cy, jup_tex(), t * 0.01)
        return camera(f, 1.0 + 0.05 * p)

    def labels(self, t):
        return [("Sun", 120, 330), ("Jupiter", 640, 680)]


class JupiterAurora:
    def __init__(self, dur, **_):
        self.incl = 0.55
        self.sph = Sphere(430, light=(-0.4, 0.2, 0.9), incl=self.incl, atm=JUP_ATM, atm_k=0.5)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 600
        self.sph.composite(f, cx, cy, jup_tex(), 0.3 + t * 0.004)
        px, py = cx, cy - 430 * math.cos(self.incl)
        ov = np.zeros_like(f, np.float32)
        for k in range(3):
            rx = 140 + 18 * k + 8 * math.sin(t * 1.3 + k)
            ry = rx * math.sin(self.incl)
            cv2.ellipse(ov, (int(px), int(py + 8)), (int(rx), int(ry)), 0, 0, 360, (255, 120, 170), 10, cv2.LINE_AA)
        ov = cv2.GaussianBlur(ov, (0, 0), 9)
        k = 0.7 + 0.3 * math.sin(t * 2.1) * math.sin(t * 0.7)
        f = np.clip(f.astype(np.float32) + ov * k * 1.6, 0, 255).astype(np.uint8)
        glow(f, px, py, 90, (255, 140, 180), 0.25 * k)
        return camera(f, 1.0 + 0.06 * p)

    def hud(self, t, p):
        return "Aurora (artist's view)"


class JupiterRings:
    def __init__(self, dur, **_):
        self.sph = Sphere(330, light=(-0.5, 0.3, 0.8), incl=0.08, atm=JUP_ATM, atm_k=0.5)

    def _ring(self, f, cx, cy, half):
        ov = np.zeros_like(f, np.float32)
        a0, a1 = (180, 360) if half == "back" else (0, 180)
        for rr, w, c in ((1.80, 6, 0.45), (1.72, 3, 0.25), (2.35, 24, 0.12), (2.9, 30, 0.06)):
            cv2.ellipse(ov, (cx, cy), (int(330 * rr), int(330 * rr * 0.14)), -8, a0, a1, (120 * c, 150 * c, 175 * c), w, cv2.LINE_AA)
        ov = cv2.GaussianBlur(ov, (0, 0), 2.5)
        return np.clip(f.astype(np.float32) + ov, 0, 255).astype(np.uint8)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 540
        f = self._ring(f, cx, cy, "back")
        self.sph.composite(f, cx, cy, jup_tex(), 0.2 + t * 0.005)
        f = self._ring(f, cx, cy, "front")
        return camera(f, 1.0 + 0.08 * p)

    def hud(self, t, p):
        return "Rings brightened to be visible"


GALILEAN = [("Io", 1.77, 5.9, 18, "io"), ("Europa", 3.55, 9.4, 16, "europa"), ("Ganymede", 7.15, 15.0, 26, "ganymede"),
            ("Callisto", 16.69, 26.4, 24, "callisto")]


class JupiterTelescope:
    """What Galileo saw: four points of light shifting from night to night."""

    def __init__(self, dur, **_):
        self.dur = dur

    def frame(self, t, p):
        f = np.zeros((H, W, 3), np.uint8)
        cx, cy, R = 960, 520, 420
        view = (space_bg(0, (0, 0)) * 0.35).astype(np.uint8)
        mask = np.zeros((H, W), np.uint8)
        cv2.circle(mask, (cx, cy), R, 255, -1, cv2.LINE_AA)
        f = np.where(mask[..., None] > 0, view, f)
        night = int(p * 6.999)
        glow(f, cx, cy, 16, (190, 225, 245), 0.9)
        cv2.circle(f, (cx, cy), 13, (210, 235, 250), -1, cv2.LINE_AA)
        self._night = night + 1
        for name, per, a, _, _ in GALILEAN:
            q = TAU * (night * 1.0 + 0.3) / per + len(name)
            x = cx + a * 13 * math.sin(q)
            cv2.circle(f, (int(x), cy), 4, (230, 240, 250), -1, cv2.LINE_AA)
            glow(f, x, cy, 6, (200, 220, 240), 0.5)
        cv2.circle(f, (cx, cy), R, (60, 60, 70), 6, cv2.LINE_AA)
        fade = min(1, (p * 7 % 1) / 0.08, (1 - p * 7 % 1) / 0.08)
        return (f.astype(np.float32) * (0.35 + 0.65 * fade)).astype(np.uint8)

    def hud(self, t, p):
        return f"January 1610, night {getattr(self, '_night', 1)}"


class JupiterMoons:
    def __init__(self, dur, **_):
        self.j = Sphere(140, light=(-0.6, 0.3, 0.74), incl=0.1, atm=JUP_ATM, atm_k=0.5)
        self.ms = {k: Sphere(r, light=(-0.6, 0.3, 0.74), atm_k=0.0, halo=0.02) for _, _, _, r, k in GALILEAN}
        self.dur = dur

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 520
        days = t / max(self.dur, 1) * 18
        orbit_px = {"io": 230, "europa": 340, "ganymede": 520, "callisto": 760}
        ov = np.zeros_like(f)
        for k, a in orbit_px.items():
            cv2.ellipse(ov, (cx, cy), (a, int(a * 0.22)), 0, 0, 360, (150, 150, 160), 1, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.45, 0)
        bodies = []
        for name, per, _, r, key in GALILEAN:
            q = TAU * days / per + len(name) * 0.9
            x, y = orbit_px[key] * math.cos(q), orbit_px[key] * math.sin(q) * 0.22
            bodies.append((y, name, x, key))
        for y, name, x, key in sorted(bodies):
            if y >= 0:
                break
            self.ms[key].composite(f, cx + x, cy + y, moon_tex(key), t * 0.05)
        self.j.composite(f, cx, cy, jup_tex(), t * 0.02)
        for y, name, x, key in sorted(bodies):
            if y >= 0:
                self.ms[key].composite(f, cx + x, cy + y, moon_tex(key), t * 0.05)
        self._pos = [(name, int(cx + x), int(cy + y + 48)) for y, name, x, key in bodies if not (y < 0 and abs(x) < 150)]
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return getattr(self, "_pos", [])


class IoVolcano:
    def __init__(self, dur, **_):
        self.io = Sphere(380, light=(-0.5, 0.3, 0.81), incl=0.1, atm_k=0.0, halo=0.02)
        self.j = Sphere(700, light=(-0.5, 0.3, 0.81), incl=0.1, atm=JUP_ATM, atm_k=0.4)
        r = np.random.default_rng(390)
        self.plumes = [(ang, r.uniform(0, 1)) for ang in (2.3, 0.5, 1.4)]
        self.pn = 260
        self.pv = r.uniform(0.6, 1.0, self.pn)
        self.pa = r.uniform(-0.5, 0.5, self.pn)
        self.pph = r.uniform(0, 1, self.pn)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        self.j.composite(f, 1750, 1000, jup_tex(), 0.3 + t * 0.003)
        cx, cy, R = 860, 540, 380
        self.io.composite(f, cx, cy, moon_tex("io"), 0.2 + t * 0.006)
        ov = np.zeros_like(f, np.float32)
        for ang, ph in self.plumes:
            nx, ny = math.cos(ang), -math.sin(ang)
            bx, by = cx + nx * R * 0.99, cy + ny * R * 0.99
            tx, ty = -ny, nx
            for v, a, q in zip(self.pv, self.pa, self.pph):
                k = (q + t * 0.25 + ph) % 1
                up = v * 4 * k * (1 - k) * 170
                side = a * k * 220
                x, y = bx + nx * up + tx * side, by + ny * up + ty * side
                cv2.circle(ov, (int(x), int(y)), 3, (200 * (1 - k * 0.5), 210, 230), -1, cv2.LINE_AA)
        ov = cv2.GaussianBlur(ov, (0, 0), 4)
        f = np.clip(f.astype(np.float32) + ov * 0.9, 0, 255).astype(np.uint8)
        return camera(f, 1.0 + 0.05 * p)

    def labels(self, t):
        return [("Io", 860, 125)]


class EuropaOcean:
    def __init__(self, dur, **_):
        self.sph = Sphere(300, light=(-0.5, 0.3, 0.81), incl=0.15, atm_k=0.0, halo=0.02)
        r = np.random.default_rng(395)
        self.bub = [(r.uniform(0, 1), r.uniform(0, 1), r.uniform(0.02, 0.06)) for _ in range(60)]

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        self.sph.composite(f, 560, 470, moon_tex("europa"), 0.3 + t * 0.006)
        k = ease(min(1, max(0, (p - 0.1) / 0.3)))
        if k > 0:
            x0, x1, y0, y1 = 1050, 1800, 170, 820
            ov = f.copy()
            ice1 = y0 + int((y1 - y0) * 0.22)
            ocean1 = y0 + int((y1 - y0) * 0.78)
            cv2.rectangle(ov, (x0, y0), (x1, ice1), (235, 228, 222), -1)
            for yy in range(ice1, ocean1):
                g = (yy - ice1) / (ocean1 - ice1)
                cv2.line(ov, (x0, yy), (x1, yy), (int(150 - 90 * g), int(90 - 50 * g), int(30 - 20 * g)), 1)
            cv2.rectangle(ov, (x0, ocean1), (x1, y1), (60, 75, 95), -1)
            for bx, by, sp in self.bub:
                yy = ocean1 - ((by + t * sp) % 1) * (ocean1 - ice1)
                cv2.circle(ov, (int(x0 + bx * (x1 - x0)), int(yy)), 3, (230, 210, 180), -1, cv2.LINE_AA)
            cv2.rectangle(ov, (x0, y0), (x1, y1), (200, 200, 210), 2)
            f = cv2.addWeighted(f, 1 - k, ov, k, 0)
            self._lab = [("Ice shell", (x0 + x1) // 2, (y0 + ice1) // 2), ("Salty ocean", (x0 + x1) // 2, (ice1 + ocean1) // 2),
                         ("Rocky interior", (x0 + x1) // 2, (ocean1 + y1) // 2)] if k > 0.6 else []
        else:
            self._lab = []
        return f

    def labels(self, t):
        return [("Europa", 560, 830)] + getattr(self, "_lab", [])

    def hud(self, t, p):
        return "Layers not to scale"


class GanymedeScale:
    def __init__(self, dur, **_):
        self.g = Sphere(300, light=(-0.5, 0.3, 0.81), incl=0.1, atm_k=0.0, halo=0.02)
        self.m = Sphere(int(300 * 4880 / 5262), light=(-0.5, 0.3, 0.81), incl=0.1, atm_k=0.0, halo=0.02)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        self.g.composite(f, 580, 470, moon_tex("ganymede"), 0.1 + t * 0.006)
        self.m.composite(f, 1360, 470 + 300 - self.m.R, texture("mercury"), 0.4 + t * 0.006)
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [("Ganymede (moon) 5,262 km", 580, 835), ("Mercury (planet) 4,880 km", 1360, 835)]


class Callisto:
    def __init__(self, dur, **_):
        self.sph = Sphere(440, light=(0.75, 0.25, 0.6), incl=0.15, atm_k=0.0, halo=0.02)

    def frame(self, t, p):
        f = space_bg(t, (3, 1))
        self.sph.composite(f, 1000, 540, moon_tex("callisto"), 0.1 + t * 0.006)
        return camera(f, 1.0 + 0.07 * p, -20 * p, 0)

    def labels(self, t):
        return [("Callisto", 1000, 60 + 20)]


class JupiterFlyby:
    def __init__(self, dur, **_):
        self.sph = Sphere(430, light=(-0.6, 0.35, 0.72), incl=0.1, atm=JUP_ATM, atm_k=0.5)

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.sph.composite(f, 1380, 600, jup_tex(), 0.2 + t * 0.004)
        draw_probe(f, -150 + 1250 * p, 260 + 120 * p, 0.9, t)
        return f


class JupiterProbe:
    """A small entry probe drifting down under its parachute into the clouds."""

    def __init__(self, dur, **_):
        self.sea = _jup_sea()

    def frame(self, t, p):
        img = self.sea.render(t, horizon=0.35 - 0.2 * p, speed=4.0, sky_top=(55, 60, 75), sky_hor=(140, 160, 185))
        img = (img.astype(np.float32) * (1 - 0.35 * p)).astype(np.uint8)
        cx = 960 + 30 * math.sin(t * 0.5)
        cy = 520 + 12 * math.sin(t * 1.1)
        cc, ct = int(cx), int(cy - 240)
        for i in range(-3, 4):
            cv2.line(img, (int(cx), int(cy - 30)), (cc + i * 30, ct + 8), (60, 60, 70), 2, cv2.LINE_AA)
        cv2.ellipse(img, (cc, ct), (120, 55), 0, 180, 360, (235, 235, 240), -1, cv2.LINE_AA)
        for i in (-2, 0, 2):
            cv2.ellipse(img, (cc, ct), (int(abs(i) * 28 + 1), 55), 0, 180, 360, (60, 110, 200), 3, cv2.LINE_AA)
        cv2.ellipse(img, (int(cx), int(cy)), (55, 32), 0, 0, 360, (150, 155, 165), -1, cv2.LINE_AA)
        cv2.ellipse(img, (int(cx), int(cy) - 6), (55, 20), 0, 180, 360, (200, 205, 210), -1, cv2.LINE_AA)
        return img

    def hud(self, t, p):
        return f"Depth about {int(150 * ease(p))} km"


class JupiterImpact:
    def __init__(self, dur, **_):
        self.sph = Sphere(430, light=(-0.4, 0.3, 0.86), incl=0.15, atm=JUP_ATM, atm_k=0.5)
        self.n = 6
        self.hits = [0.12 + 0.11 * k for k in range(self.n)]
        self.dur = dur

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 1100, 560
        done = sum(1 for h in self.hits if p >= h)
        # scars appear at lon u 0.18..; rotate so they come round to face us
        self.sph.composite(f, cx, cy, jup_tex(done), 0.03 + 0.3 * p)
        hx, hy = cx - 430 * 0.93, cy + 430 * 0.32
        for k, h in enumerate(self.hits):
            start = h - 0.16
            if start <= p < h:
                q = (p - start) / 0.16
                x = 80 + (hx - 80) * q + k * 6
                y = 120 + (hy - 120) * q
                glow(f, x, y, 9, (230, 240, 255), 0.9)
                cv2.line(f, (int(x), int(y)), (int(x - 60), int(y - 40)), (180, 200, 220), 2, cv2.LINE_AA)
            if h <= p < h + 0.05:
                k2 = 1 - (p - h) / 0.05
                glow(f, hx, hy, 50, (200, 235, 255), 1.2 * k2)
        return camera(f, 1.0 + 0.04 * p)

    def hud(self, t, p):
        done = sum(1 for h in self.hits if p >= h)
        return f"Impacts: {done}" if done else "July 1994"


class JupiterJuice:
    """A spacecraft circling Ganymede, with Jupiter looming behind."""

    def __init__(self, dur, **_):
        self.g = Sphere(300, light=(-0.6, 0.3, 0.74), incl=0.1, atm_k=0.0, halo=0.02)
        self.j = Sphere(560, light=(-0.6, 0.3, 0.74), incl=0.1, atm=JUP_ATM, atm_k=0.5)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        self.j.composite(f, 1650, 320, jup_tex(), 0.4 + t * 0.004)
        cx, cy = 820, 600
        q = t * 0.35
        x, y = cx + 470 * math.cos(q), cy + 120 * math.sin(q)
        if math.sin(q) < 0:
            draw_probe(f, x, y, 0.35, t)
        self.g.composite(f, cx, cy, moon_tex("ganymede"), 0.2 + t * 0.006)
        if math.sin(q) >= 0:
            draw_probe(f, x, y, 0.45, t)
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [("Ganymede", 820, 250)]


TABLE = {
    "jupiter_scale": JupiterScale, "jupiter_orbits": JupiterOrbits, "jupiter_bands": JupiterBands, "jupiter_dive": JupiterDive,
    "jupiter_spot": JupiterSpot, "jupiter_poles": JupiterPoles, "jupiter_interior": JupiterInterior,
    "jupiter_magneto": JupiterMagneto, "jupiter_aurora": JupiterAurora, "jupiter_rings": JupiterRings,
    "jupiter_telescope": JupiterTelescope, "jupiter_moons": JupiterMoons, "io_volcano": IoVolcano,
    "europa_ocean": EuropaOcean, "ganymede_scale": GanymedeScale, "callisto": Callisto, "jupiter_flyby": JupiterFlyby,
    "jupiter_probe": JupiterProbe, "jupiter_impact": JupiterImpact, "jupiter_juice": JupiterJuice,
}
VARIANT = {"jupiter_closeup": JupiterCloseup}
VISUALS = set(TABLE) | set(VARIANT)


def make(visual, dur, occurrence):
    if visual in VARIANT:
        return VARIANT[visual](dur, variant=occurrence)
    return TABLE[visual](dur)
