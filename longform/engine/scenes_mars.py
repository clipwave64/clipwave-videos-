"""Scene library for the Mars long-form video. Every visual is generated in code (no downloaded footage)."""
import math
import numpy as np
import cv2
import gfx
from gfx import W, H, Sphere, texture, space_bg, add_layer, glow, smoothstep, fbm, ramp
from scenes import ease, camera, draw_probe, shimmer, Orbits, TAU

_tex = {}


def mars_tex(kind="plain"):
    """Procedural Mars map (BGR). kinds: plain, canyon, dusty, wet."""
    if kind in _tex:
        return _tex[kind]
    th, tw = 1024, 2048
    lat = np.linspace(math.pi / 2, -math.pi / 2, th, dtype=np.float32)[:, None]
    lon = np.linspace(0, 1, tw, dtype=np.float32)[None, :]
    a = fbm(th, tw, 2.2, 101)
    b = fbm(th, tw, 1.6, 102)
    dark = smoothstep(0.55, 0.7, fbm(th, tw, 2.6, 103, ax=1.5))
    x = 0.65 * a + 0.35 * b
    t = ramp(x, [(0, (120, 52, 28)), (0.35, (165, 78, 40)), (0.6, (196, 108, 60)), (0.85, (220, 145, 92)), (1, (236, 178, 128))])
    t = t * (1 - 0.45 * dark[..., None])
    # craters
    r = np.random.default_rng(104)
    img = np.zeros((th, tw), np.float32)
    for _ in range(260):
        cx, cy = r.uniform(0, tw), r.uniform(th * 0.12, th * 0.9)
        rad = r.uniform(2, 11) * (1 + 1.5 * (r.random() < 0.05))
        cv2.circle(img, (int(cx), int(cy)), int(rad), -0.10, -1, cv2.LINE_AA)
        cv2.ellipse(img, (int(cx), int(cy)), (int(rad), int(rad)), 0, 200, 340, 0.06, max(1, int(rad * 0.3)), cv2.LINE_AA)
    img = cv2.GaussianBlur(img, (0, 0), 2.0)
    t = t * (1 + img[..., None])
    if kind == "canyon" or kind == "plain" or kind == "dusty":
        # Valles Marineris: a long dark gash just south of the equator, near lon 0.3-0.5
        u = lon + 0.012 * (fbm(th, tw, 2.4, 105) - 0.5)
        yc = 0.5 + 0.06 + 0.01 * np.sin(u * 40)
        vv = np.linspace(0, 1, th, dtype=np.float32)[:, None]
        width = 0.011 + 0.007 * np.sin((u - 0.3) / 0.2 * math.pi)
        m = smoothstep(width, width * 0.3, np.abs(vv - yc)) * ((u > 0.3) & (u < 0.5))
        t = t * (1 - 0.6 * m[..., None]) + np.array([60, 25, 15], np.float32) * 0.6 * m[..., None]
        # Tharsis volcanoes: bright domes with dark summit pits, west of the canyon
        for (vu, vvv, rr) in [(0.22, 0.43, 34), (0.27, 0.48, 18), (0.28, 0.52, 18), (0.29, 0.56, 18)]:
            cx, cy = int(vu * tw), int(vvv * th)
            ov = t.copy()
            cv2.circle(ov, (cx, cy), rr, (205, 140, 95), -1, cv2.LINE_AA)
            cv2.circle(ov, (cx, cy), max(3, rr // 5), (120, 60, 35), -1, cv2.LINE_AA)
            t = cv2.addWeighted(t, 0.45, cv2.GaussianBlur(ov, (0, 0), 3), 0.55, 0)
        t = cv2.GaussianBlur(t, (0, 0), 1.0)
    polar = smoothstep(1.28, 1.4, np.abs(lat) + 0.08 * (a - 0.5))
    t = t * (1 - polar[..., None]) + np.array([245, 240, 235], np.float32) * polar[..., None]
    if kind == "dusty":
        t = t * 0.15 + np.array([205, 140, 95], np.float32) * 0.85
    if kind == "wet":
        north = smoothstep(0.0, 0.25, lat) * smoothstep(0.62, 0.5, a)
        water = ramp(a, [(0, (10, 40, 90)), (0.6, (30, 80, 140))])
        t = t * (1 - north[..., None]) + water * north[..., None]
        cl = smoothstep(0.62, 0.85, fbm(th, tw, 2.0, 106, ax=2.5))
        t = t * (1 - 0.7 * cl[..., None]) + 240 * 0.7 * cl[..., None]
    t = np.clip(t, 0, 255).astype(np.uint8)[..., ::-1].copy()
    _tex[kind] = t
    return t


MARS_ATM = (240, 170, 120)     # RGB rim colour


class MarsCloseup:
    """Variants: 0 intro approach, 1 side-lit drift, 2 huge limb view, 3+ slow spin."""

    def __init__(self, dur, variant=0, **_):
        self.v = variant % 4
        if self.v == 2:
            self.sph = Sphere(820, light=(-0.75, 0.45, 0.5), incl=0.35, atm=MARS_ATM, atm_k=0.7)
        elif self.v == 1:
            self.sph = Sphere(440, light=(0.7, 0.2, 0.68), incl=0.2, atm=MARS_ATM, atm_k=0.6)
        else:
            self.sph = Sphere(470, light=(-0.55, 0.3, 0.78), incl=0.3, atm=MARS_ATM, atm_k=0.6)
        self.tex = mars_tex("plain")

    def frame(self, t, p):
        f = space_bg(t, (4, 1.5))
        if self.v == 0:
            sc = 0.32 + 0.73 * ease(min(1, p * 1.25))
            self.sph.composite(f, 1060 + 120 * (1 - sc), 540, self.tex, 0.3 + t * 0.003, scale=sc)
            return camera(f, 1 + 0.03 * p)
        if self.v == 1:
            self.sph.composite(f, 760, 560, self.tex, 0.55 + t * 0.003)
            return camera(f, 1.0 + 0.08 * p, -30 * p, 0)
        if self.v == 2:
            self.sph.composite(f, 1300, 1250, self.tex, 0.1 + t * 0.006)
            return camera(f, 1.0 + 0.05 * p)
        self.sph.composite(f, 960, 560, self.tex, 0.8 + t * 0.004)
        return camera(f, 1.0 + 0.05 * p)


class MarsTwins:
    def __init__(self, dur, **_):
        self.m = Sphere(170, light=(-0.4, 0.25, 0.88), atm=MARS_ATM, atm_k=0.6)
        self.e = Sphere(330, light=(-0.4, 0.25, 0.88), atm=(130, 180, 255), atm_k=1.2)

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.e.composite(f, 640, 420, texture("earth"), 0.3 + t * 0.006)
        self.m.composite(f, 1400, 420 + 160, mars_tex(), 0.3 + t * 0.006)
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [("EARTH", 640, 800), ("MARS", 1400, 800)]


class MarsOrbits(Orbits):
    def __init__(self, dur, variant=0, **_):
        self.dur, self.v = dur, variant
        self.S = 380
        self.tilt = 0.36
        self.tex = {"earth": texture("earth"), "mars": mars_tex()}
        self.planets = [("earth", 1.0, 365.25, 22, 0.4), ("mars", 1.52, 687.0, 16, 2.0)]
        self.days_per_sec = (687 * 1.03) / max(dur, 1)

    def frame(self, t, p):
        f = space_bg(t, (1, 0))
        f = (f * 0.7).astype(np.uint8)
        ov = np.zeros_like(f)
        th = np.linspace(0, TAU, 240)
        for name, a, per, r, ph in self.planets:
            pts = np.array([self.proj(a * math.cos(q), a * math.sin(q)) for q in th], np.int32)
            col = (90, 130, 240) if name == "mars" else (170, 170, 170)
            cv2.polylines(ov, [pts], True, col, 2, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.5, 0)
        days = t * self.days_per_sec
        bodies = [(0.0, "sun", 0, 0)]
        for name, a, per, r, ph in self.planets:
            q = ph + TAU * days / per
            bodies.append((a * math.sin(q), name, a * math.cos(q), r))
        for y, name, x, r in sorted(bodies):
            if name == "sun":
                glow(f, 960, 560, 70, (110, 200, 255), 1.0)
                cv2.circle(f, (960, 560), 38, (225, 250, 255), -1, cv2.LINE_AA)
                continue
            sx, sy = self.proj(x, y)
            L = np.array([960 - sx, sy - 560, 30.0]); n = np.linalg.norm(L)
            sph = Sphere(r, light=(L[0] / n, L[1] / n, max(L[2] / n, 0.15)), halo=0.25, atm_k=0.9,
                         atm=(150, 200, 255) if name == "earth" else MARS_ATM)
            sph.composite(f, sx, sy, self.tex[name], t * 0.05)
        return camera(f, 1.04 - 0.04 * p)

    def hud(self, t, p):
        return f"{min(687, int(t * self.days_per_sec))} Earth days"


_terr = {}


def mars_terrain(kind):
    if kind in _terr:
        return _terr[kind]
    tr = gfx.Terrain(seed=201 if kind == "plains" else 211, kind="plains" if kind == "plains" else "hills")
    if kind == "plains":
        # gentler, sandier plains; scatter some boulders
        tr.h = tr.h * 0.6
    if kind == "shield":
        s = tr.size
        tr.h *= 0.25
        ys, xs = np.mgrid[0:s, 0:s].astype(np.float32)
        dx = (xs - 512 + s / 2) % s - s / 2
        dy = (ys - 300 + s / 2) % s - s / 2
        d = np.sqrt(dx * dx + dy * dy) / 420
        cone = (1 - np.clip(d, 0, 1) ** 1.8) * 150 * (d < 1)
        cald = smoothstep(0.1, 0.06, d) * 25
        tr.h += cone - cald
        tr.h = cv2.GaussianBlur(tr.h, (0, 0), 3)
        gy, gx = np.gradient(tr.h)
        n = np.dstack([-gx, -gy, np.ones_like(gx) * 1.6]); n /= np.linalg.norm(n, axis=2, keepdims=True)
        sun = np.array([0.4, -0.3, 0.85]); sun /= np.linalg.norm(sun)
        lam = np.clip((n * sun).sum(2), 0, 1)
        tone = fbm(s, s, 1.5, 214)
        col = ramp(0.6 * tone + 0.4 * np.clip(tr.h / 260, 0, 1), [(0, (95, 45, 25)), (0.5, (160, 80, 42)), (1, (205, 130, 80))])
        col *= (0.35 + 0.75 * lam)[..., None]
        tr.col = np.clip(col, 0, 255).astype(np.float32)[..., ::-1].copy()
    else:
        s = tr.size
        tone = fbm(s, s, 1.5, 215)
        base = tr.col[..., ::-1].mean(2) / 160
        col = ramp(np.clip(0.5 * tone + 0.5 * base, 0, 1), [(0, (80, 38, 20)), (0.5, (150, 72, 38)), (1, (210, 125, 75))])
        tr.col = np.clip(col * (0.6 + 0.6 * base[..., None]), 0, 255).astype(np.float32)[..., ::-1].copy()
    _terr[kind] = tr
    return tr


SKY_TOP = (95, 135, 185)     # BGR butterscotch
SKY_HOR = (150, 190, 225)
FOG = (120, 160, 205)


class MarsSurface:
    def __init__(self, dur, variant=0, **_):
        self.v = variant % 3
        self.tr = mars_terrain("plains")

    def frame(self, t, p):
        yaw = [0.35, 2.1, 4.0][self.v]
        img = self.tr.render(100 + 300 * self.v + t * 1.2, 100 + t * 0.5, yaw + 0.05 * math.sin(t * 0.1), cam_alt=4.5,
                             pitch=-0.05, fog_col=FOG, fog_dist=520, sky_top=SKY_TOP, sky_hor=SKY_HOR)
        return img


class MarsVolcano:
    def __init__(self, dur, **_):
        self.tr = mars_terrain("shield")

    def frame(self, t, p):
        cy = 300 + 1000 - 200 * ease(p)
        return self.tr.render(512 + 40 * math.sin(p * 2), cy, -math.pi / 2, cam_alt=30 + 25 * p, pitch=0.04,
                              fog_col=FOG, fog_dist=900, sky_top=SKY_TOP, sky_hor=SKY_HOR)


class MarsCanyon:
    def __init__(self, dur, **_):
        self.sph = Sphere(470, light=(-0.35, 0.3, 0.88), incl=0.05, atm=MARS_ATM, atm_k=0.6)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        # turn so the canyon (u 0.3-0.5) swings to face us
        self.sph.composite(f, 960, 540, mars_tex("canyon"), 0.62 - 0.12 * ease(p))
        return camera(f, 1.0 + 0.35 * ease(p), 0, -120 * ease(p))


class MarsDustStorm:
    def __init__(self, dur, **_):
        self.sph = Sphere(440, light=(-0.5, 0.3, 0.81), incl=0.3, atm=MARS_ATM, atm_k=0.9)

    def frame(self, t, p):
        f = space_bg(t, (3, 1))
        m = smoothstep(0.08, 0.8, np.float32(p)).item()
        ra, aa = self.sph.layer(mars_tex("plain"), 0.4 + t * 0.004)
        rb, ab = self.sph.layer(mars_tex("dusty"), 0.4 + t * 0.004)
        add_layer(f, ra * (1 - m) + rb * m, aa, 960, 560)
        return camera(f, 1.0 + 0.05 * p)

    def hud(self, t, p):
        return "Global dust storm" if p > 0.45 else "Dust storm spreading"


class MarsDustDevil:
    def __init__(self, dur, **_):
        self.tr = mars_terrain("plains")
        r = np.random.default_rng(220)
        self.n = 900
        self.h = r.uniform(0, 1, self.n) ** 0.8
        self.a = r.uniform(0, TAU, self.n)
        self.sp = r.uniform(2.5, 5.0, self.n)

    def frame(self, t, p):
        img = self.tr.render(700 + t * 0.6, 400, 1.2, cam_alt=4.0, pitch=-0.02, fog_col=FOG, fog_dist=520,
                             sky_top=SKY_TOP, sky_hor=SKY_HOR)
        cx = 1300 - 260 * p
        base_y, top_y = 640, 60
        ov = np.zeros_like(img, np.float32)
        for h, a, sp in zip(self.h, self.a, self.sp):
            y = base_y - h * (base_y - top_y)
            rad = 25 + 110 * h ** 1.3
            ang = a + t * sp
            x = cx + rad * math.cos(ang) + 8 * math.sin(t * 0.8 + h * 5)
            depth = 0.55 + 0.45 * math.sin(ang)
            cv2.circle(ov, (int(x), int(y)), 3, (110 * depth, 150 * depth, 195 * depth), -1, cv2.LINE_AA)
        ov = cv2.GaussianBlur(ov, (0, 0), 12)
        a = np.clip(ov.mean(2, keepdims=True) / 40, 0, 0.7)
        dust = np.array([120, 160, 205], np.float32)
        return np.clip(img.astype(np.float32) * (1 - a) + dust * a, 0, 255).astype(np.uint8)


class MarsSunset:
    def __init__(self, dur, **_):
        def ridge(seed, amp, base, rough):
            n = fbm(64, 2048, rough, seed)[32][:W]
            return (base - amp * n).astype(np.int32)
        self.r1 = ridge(231, 160, 930, 2.2)
        self.r2 = ridge(232, 90, 1040, 2.6)

    def frame(self, t, p):
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        top = np.array([40, 45, 70], np.float32) * (1 - 0.5 * p)
        hor = np.array([90, 120, 160], np.float32) * (1 - 0.4 * p)
        img = np.broadcast_to(top * (1 - g) + hor * g, (H, W, 3)).astype(np.float32).copy()
        stars = space_bg(0, (0, 0)).astype(np.float32) * (0.05 + 0.4 * p) * (1 - g) ** 2
        img = np.clip(img + stars, 0, 255).astype(np.uint8)
        sx, sy = 980, int(640 + 260 * ease(p))
        glow(img, sx, sy, 230, (230, 150, 80), 0.75)          # blue halo (BGR)
        glow(img, sx, sy, 70, (255, 215, 170), 0.8)
        cv2.circle(img, (sx, sy), 16, (255, 245, 235), -1, cv2.LINE_AA)
        for ys, col in [(self.r1, (30, 40, 70)), (self.r2, (12, 16, 30))]:
            pts = np.vstack([np.c_[np.arange(W), ys], [[W, H], [0, H]]]).astype(np.int32)
            cv2.fillPoly(img, [pts], col, cv2.LINE_AA)
        return camera(img, 1.02 + 0.03 * p)


class MarsPoles:
    def __init__(self, dur, **_):
        self.sph = Sphere(460, light=(-0.4, -0.2, 0.9), incl=-0.9, atm=MARS_ATM, atm_k=0.6)
        r = np.random.default_rng(240)
        self.fx, self.fy = r.uniform(0, W, 400), r.uniform(0, H, 400)
        self.fs = r.uniform(0.5, 1.5, 400)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        self.sph.composite(f, 960, 560, mars_tex(), t * 0.01)
        ov = np.zeros_like(f)
        for x, y, s in zip(self.fx, self.fy, self.fs):
            yy = (y + t * 40 * s) % H
            cv2.circle(ov, (int(x + 10 * math.sin(t + y)), int(yy)), int(1 + s * 1.5), (250, 250, 255), -1, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.5 * smoothstep(0.1, 0.4, np.float32(p)).item(), 0)
        return camera(f, 1.0 + 0.06 * p)

    def labels(self, t):
        return [("South polar cap", 960, 1000)]


class MarsMoons:
    def __init__(self, dur, variant=0, **_):
        self.v = variant
        self.m = Sphere(260, light=(-0.6, 0.3, 0.74), incl=0.3, atm=MARS_ATM, atm_k=0.6)
        self.ph = Sphere(30, light=(-0.6, 0.3, 0.74), atm_k=0.0, halo=0.02)
        self.de = Sphere(20, light=(-0.6, 0.3, 0.74), atm_k=0.0, halo=0.02)
        self.dur = dur

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 540
        # Mars spin period ~ 24.6 h, Phobos 7.65 h, Deimos 30.3 h. Show ~1.2 Mars days over the scene.
        hours = t / max(self.dur, 1) * 30
        bodies = []
        for name, a, per, sph in (("Phobos", 380, 7.65, self.ph), ("Deimos", 620, 30.3, self.de)):
            q = TAU * hours / per + (0.7 if name == "Deimos" else 0)
            x, y = a * math.cos(q), a * math.sin(q) * 0.28
            bodies.append((y, name, x, sph))
        ov = np.zeros_like(f)
        for a in (380, 620):
            cv2.ellipse(ov, (cx, cy), (a, int(a * 0.28)), 0, 0, 360, (150, 150, 160), 1, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.45, 0)
        behind = [b for b in bodies if b[0] < 0]
        front = [b for b in bodies if b[0] >= 0]
        for y, name, x, sph in behind:
            sph.composite(f, cx + x, cy + y, texture("rock_small"), t * 0.1, scale=1.0)
        self.m.composite(f, cx, cy, mars_tex(), TAU * hours / 24.6 / TAU)
        for y, name, x, sph in front:
            sph.composite(f, cx + x, cy + y, texture("rock_small"), t * 0.1, scale=1.0)
        self._pos = [(name, cx + x, cy + y, y) for y, name, x, sph in bodies]
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [(n, int(x), int(y + 40)) for n, x, y, d in getattr(self, "_pos", []) if not (d < 0 and abs(x - 960) < 260)]

    def hud(self, t, p):
        return f"{int(p * 30)} hours"


class MarsWet:
    def __init__(self, dur, **_):
        self.sph = Sphere(440, light=(-0.5, 0.3, 0.81), incl=0.45, atm=(130, 180, 255), atm_k=1.0)

    def frame(self, t, p):
        f = space_bg(t, (3, 1))
        m = smoothstep(0.55, 0.95, np.float32(p)).item()
        ra, aa = self.sph.layer(mars_tex("wet"), 0.2 + t * 0.004)
        rb, ab = self.sph.layer(mars_tex("plain"), 0.2 + t * 0.004)
        add_layer(f, ra * (1 - m) + rb * m, aa, 1000, 560)
        return camera(f, 1.06 - 0.06 * p)

    def hud(self, t, p):
        return "Billions of years ago (artist's idea)" if p < 0.6 else "Mars today"


def draw_rover(img, x, y, s, t):
    x, y = int(x), int(y)
    body = (205, 210, 215)
    dark = (60, 60, 65)
    for k in (-1, 0, 1):
        wx = x + int(k * 70 * s)
        cv2.circle(img, (wx, y + int(10 * s)), int(22 * s), dark, -1, cv2.LINE_AA)
        a = t * 2 + k
        cv2.line(img, (wx, y + int(10 * s)), (wx + int(15 * s * math.cos(a)), y + int(10 * s + 15 * s * math.sin(a))), (120, 120, 125), 2, cv2.LINE_AA)
    cv2.line(img, (x - int(80 * s), y - int(12 * s)), (x + int(80 * s), y - int(12 * s)), (150, 150, 155), int(5 * s), cv2.LINE_AA)
    cv2.rectangle(img, (x - int(75 * s), y - int(55 * s)), (x + int(65 * s), y - int(18 * s)), body, -1, cv2.LINE_AA)
    cv2.rectangle(img, (x - int(75 * s), y - int(55 * s)), (x + int(65 * s), y - int(48 * s)), (230, 235, 240), -1, cv2.LINE_AA)
    cv2.line(img, (x + int(40 * s), y - int(55 * s)), (x + int(40 * s), y - int(120 * s)), (190, 190, 195), int(5 * s), cv2.LINE_AA)
    cv2.rectangle(img, (x + int(22 * s), y - int(140 * s)), (x + int(62 * s), y - int(118 * s)), (170, 175, 180), -1, cv2.LINE_AA)
    cv2.circle(img, (x + int(52 * s), y - int(129 * s)), int(5 * s), (40, 40, 45), -1, cv2.LINE_AA)
    cv2.line(img, (x - int(55 * s), y - int(55 * s)), (x - int(55 * s), y - int(85 * s)), (180, 180, 185), int(3 * s), cv2.LINE_AA)


class MarsRover:
    def __init__(self, dur, variant=0, **_):
        self.v = variant
        self.tr = mars_terrain("plains")

    def frame(self, t, p):
        img = self.tr.render(300 + 200 * self.v + t * 0.8, 600, 0.9 + 0.6 * self.v, cam_alt=3.5, pitch=-0.05,
                             fog_col=FOG, fog_dist=520, sky_top=SKY_TOP, sky_hor=SKY_HOR)
        x = 500 + 900 * p
        y = 820 + 6 * math.sin(t * 1.5)
        ov = img.copy()
        cv2.ellipse(ov, (int(x), int(y + 34)), (130, 16), 0, 0, 360, (40, 50, 70), -1, cv2.LINE_AA)
        img = cv2.addWeighted(img, 0.6, ov, 0.4, 0)
        draw_rover(img, x, y, 1.5, t)
        return img


class MarsHeli:
    def __init__(self, dur, **_):
        self.tr = mars_terrain("plains")

    def frame(self, t, p):
        img = self.tr.render(900 + t * 0.4, 200, 2.6, cam_alt=4.0, pitch=-0.04, fog_col=FOG, fog_dist=520,
                             sky_top=SKY_TOP, sky_hor=SKY_HOR)
        lift = ease(min(1, p / 0.3))
        x = 960 + 250 * math.sin(p * 2.5)
        y = 820 - 420 * lift + 10 * math.sin(t * 2)
        ov = img.copy()
        cv2.ellipse(ov, (int(x), 860), (int(70 - 30 * lift), 10), 0, 0, 360, (40, 50, 70), -1, cv2.LINE_AA)
        img = cv2.addWeighted(img, 0.65, ov, 0.35, 0)
        x, y = int(x), int(y)
        for dx in (-40, 40):
            cv2.line(img, (x, y + 10), (x + dx, y + 60), (60, 60, 65), 3, cv2.LINE_AA)
        cv2.rectangle(img, (x - 28, y - 10), (x + 28, y + 22), (215, 215, 220), -1, cv2.LINE_AA)
        cv2.line(img, (x, y - 10), (x, y - 70), (90, 90, 95), 4, cv2.LINE_AA)
        for k, h in enumerate((-60, -45)):
            ph = t * 25 + k
            w = int(150 * abs(math.cos(ph)) + 20)
            cv2.ellipse(img, (x, y + h), (w, 6), 0, 0, 360, (70, 70, 75), -1, cv2.LINE_AA)
        cv2.rectangle(img, (x - 22, y - 80), (x + 22, y - 74), (40, 60, 120), -1)
        return img


class MarsFlyby:
    def __init__(self, dur, **_):
        self.sph = Sphere(430, light=(-0.6, 0.35, 0.72), incl=0.25, atm=MARS_ATM, atm_k=0.6)

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.sph.composite(f, 1380, 600, mars_tex(), 0.2 + t * 0.004)
        draw_probe(f, -150 + 1250 * p, 260 + 120 * p, 0.9, t)
        return f


class MarsDescent:
    def __init__(self, dur, **_):
        self.tr = mars_terrain("plains")

    def frame(self, t, p):
        alt = 140 - 125 * ease(p)
        img = self.tr.render(600, 600 + t * 2, 0.5, cam_alt=alt, pitch=-0.35, fog_col=FOG, fog_dist=700,
                             sky_top=SKY_TOP, sky_hor=SKY_HOR)
        cx = 960 + 30 * math.sin(t * 0.7)
        cy = 520 + 10 * math.sin(t * 1.3)
        sway = 4 * math.sin(t * 0.7)
        cc, cyy = int(cx + sway * 3), int(cy - 300)
        for i in range(-3, 4):
            cv2.line(img, (int(cx), int(cy - 40)), (cc + i * 38, cyy + 10), (60, 60, 70), 2, cv2.LINE_AA)
        cv2.ellipse(img, (cc, cyy), (150, 70), 0, 180, 360, (235, 235, 240), -1, cv2.LINE_AA)
        for i in (-2, 0, 2):
            cv2.ellipse(img, (cc, cyy), (int(abs(i) * 35 + 1), 70), 0, 180, 360, (40, 80, 220), 4, cv2.LINE_AA)
        pts = np.array([[cx - 90, cy - 40], [cx + 90, cy - 40], [cx + 55, cy + 30], [cx - 55, cy + 30]], np.int32)
        cv2.fillPoly(img, [pts], (175, 180, 190), cv2.LINE_AA)
        cv2.polylines(img, [pts], True, (110, 110, 120), 2, cv2.LINE_AA)
        return img

    def hud(self, t, p):
        return f"Altitude {max(0, int(2000 * (1 - ease(p)) ** 2))} m"


class MarsTransfer:
    def __init__(self, dur, **_):
        self.S = 360
        self.dur = dur

    def proj(self, x, y):
        return 960 + x * self.S, 560 + y * self.S * 0.42

    def frame(self, t, p):
        f = (space_bg(t, (1, 0)) * 0.7).astype(np.uint8)
        ov = np.zeros_like(f)
        th = np.linspace(0, TAU, 240)
        for a, col in ((1.0, (170, 170, 170)), (1.52, (90, 130, 240))):
            pts = np.array([self.proj(a * math.cos(q), a * math.sin(q)) for q in th], np.int32)
            cv2.polylines(ov, [pts], True, col, 2, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.5, 0)
        glow(f, 960, 560, 60, (110, 200, 255), 1.0)
        cv2.circle(f, (960, 560), 32, (225, 250, 255), -1, cv2.LINE_AA)
        # half-ellipse transfer from Earth (angle pi) to Mars (angle 0)
        a_t, e = (1.0 + 1.52) / 2, (1.52 - 1.0) / (1.52 + 1.0)
        k = ease(min(1, max(0, (p - 0.08) / 0.8)))
        nu = math.pi * (1 + k)
        trail = []
        for kk in np.linspace(0, k, 80):
            q = math.pi * (1 + kk)
            r = a_t * (1 - e * e) / (1 + e * math.cos(q - math.pi))
            trail.append(self.proj(r * math.cos(q), r * math.sin(q)))
        if len(trail) > 1:
            cv2.polylines(f, [np.array(trail, np.int32)], False, (120, 230, 255), 2, cv2.LINE_AA)
        r = a_t * (1 - e * e) / (1 + e * math.cos(nu - math.pi))
        sx, sy = self.proj(r * math.cos(nu), r * math.sin(nu))
        glow(f, sx, sy, 10, (200, 240, 255), 1.0)
        # planets: Earth starts at pi, Mars arrives at 0 at the end (Mars lead ~44 deg at launch)
        days = 259 * k
        qe = math.pi + TAU * days / 365.25
        qm = TAU * (days - 259) / 687.0
        for q, a, tex, rr, atm in ((qe, 1.0, texture("earth"), 20, (150, 200, 255)), (qm, 1.52, mars_tex(), 15, MARS_ATM)):
            px, py = self.proj(a * math.cos(q), a * math.sin(q))
            L = np.array([960 - px, py - 560, 30.0]); n = np.linalg.norm(L)
            Sphere(rr, light=(L[0] / n, L[1] / n, max(L[2] / n, 0.15)), atm=atm, atm_k=0.8, halo=0.25).composite(f, px, py, tex, t * 0.05)
        return camera(f, 1.03 - 0.03 * p)

    def hud(self, t, p):
        k = ease(min(1, max(0, (p - 0.08) / 0.8)))
        return f"Day {int(259 * k)} of the trip"


TABLE = {
    "mars_twins": MarsTwins, "mars_orbits": MarsOrbits, "mars_volcano": MarsVolcano, "mars_canyon": MarsCanyon,
    "mars_dust_storm": MarsDustStorm, "mars_dust_devil": MarsDustDevil, "mars_sunset": MarsSunset,
    "mars_poles": MarsPoles, "mars_wet": MarsWet, "mars_heli": MarsHeli, "mars_flyby": MarsFlyby,
    "mars_descent": MarsDescent, "mars_transfer": MarsTransfer,
}
VARIANT = {"mars_closeup": MarsCloseup, "mars_surface": MarsSurface, "mars_moons": MarsMoons, "mars_rover": MarsRover}


def make(visual, dur, occurrence):
    if visual in VARIANT:
        return VARIANT[visual](dur, variant=occurrence)
    return TABLE[visual](dur)
