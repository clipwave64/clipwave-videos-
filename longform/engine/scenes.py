"""Scene library for the Venus long-form video. Every visual is generated in code (no downloaded footage)."""
import math
import numpy as np
import cv2
import gfx
from gfx import W, H, Sphere, texture, space_bg, add_layer, glow, smoothstep

TAU = 2 * math.pi


def ease(p):
    return 0.5 - 0.5 * math.cos(math.pi * min(max(p, 0), 1))


def camera(frame, zoom=1.0, px=0.0, py=0.0):
    if abs(zoom - 1) < 1e-4 and px == 0 and py == 0:
        return frame
    M = np.float32([[zoom, 0, (1 - zoom) * W / 2 + px], [0, zoom, (1 - zoom) * H / 2 + py]])
    return cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def blend_add(frame, overlay, alpha):
    return cv2.addWeighted(frame, 1.0, overlay, alpha, 0)


# ------------------------------------------------------------------ planet scenes
class VenusCloseup:
    """Variants: 0 = intro approach, 1 = side-lit slow drift, 2 = huge limb view."""

    def __init__(self, dur, variant=0, **_):
        self.dur, self.v = dur, variant
        if variant == 2:
            self.sph = Sphere(820, light=(-0.75, 0.45, 0.5), incl=0.35, atm_k=1.2)
        elif variant == 1:
            self.sph = Sphere(440, light=(0.7, 0.2, 0.68), incl=0.2)
        else:
            self.sph = Sphere(470, light=(-0.55, 0.3, 0.78), incl=0.28)
        self.tex = texture("venus_clouds")

    def frame(self, t, p):
        f = space_bg(t, (4, 1.5))
        if self.v == 0:
            sc = 0.32 + 0.73 * ease(min(1, p * 1.25))
            self.sph.composite(f, 1060 + 120 * (1 - sc), 540, self.tex, 0.02 + t * 0.003, scale=sc)
            return camera(f, 1 + 0.03 * p)
        if self.v == 1:
            self.sph.composite(f, 760, 560, self.tex, 0.4 + t * 0.003)
            return camera(f, 1.0 + 0.08 * p, -30 * p, 0)
        self.sph.composite(f, 1300, 1250, self.tex, 0.7 + t * 0.006)
        return camera(f, 1.0 + 0.05 * p)


class VenusSpace:
    def __init__(self, dur, **_):
        self.sph = Sphere(360, light=(0.92, 0.25, -0.3), incl=0.25, atm_k=1.6, halo=0.16)
        self.tex = texture("venus_clouds")

    def frame(self, t, p):
        f = space_bg(t, (-5, 1))
        glow(f, 1900, 120, 260, (120, 190, 255), 0.55)
        self.sph.composite(f, 900, 560, self.tex, t * 0.003)
        return camera(f, 1.12 - 0.12 * p, 40 * p, 0)


class VenusSpin:
    def __init__(self, dur, **_):
        self.sph = Sphere(400, light=(-0.45, 0.3, 0.84), incl=0.3)
        self.tex = texture("venus_surface")

        def marker(col, u, v):
            m = (np.abs(((u + 0.5) % 1.0) - 0.5) < 0.004) & (v > 0.1) & (v < 0.9)
            col[m] = (255, 235, 140)
            return col
        self.marker = marker

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 560
        # axis line (tilted by inclination) drawn behind and in front
        ov = np.zeros_like(f)
        cv2.line(ov, (cx, cy - 520), (cx, cy + 520), (200, 220, 255), 2, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.45, 0)
        # retrograde: turn the other way; one full turn during most of the scene
        lon = 0.15 - ease(min(1, p / 0.92)) * 1.0
        self.sph.composite(f, cx, cy, self.tex, lon, extra=self.marker)
        return camera(f, 1.0 + 0.04 * p)

    def hud(self, t, p):
        d = int(round(243 * ease(min(1, p / 0.92))))
        return f"Day {d} of 243"


class Orbits:
    def __init__(self, dur, variant=0, **_):
        self.dur, self.v = dur, variant
        self.S = 640
        self.tilt = 0.36
        self.tex = {"mercury": texture("mercury"), "venus": texture("venus_clouds"), "earth": texture("earth")}
        self.planets = [("mercury", 0.39, 88.0, 12, 1.2), ("venus", 0.72, 224.7, 24, 3.4), ("earth", 1.0, 365.25, 25, 0.4)]
        self.days_per_sec = (224.7 * 1.05) / max(dur, 1)

    def proj(self, x, y):
        return 960 + x * self.S, 560 + y * self.S * self.tilt

    def frame(self, t, p):
        f = space_bg(t, (1, 0))
        f = (f * 0.7).astype(np.uint8)
        ov = np.zeros_like(f)
        th = np.linspace(0, TAU, 240)
        for name, a, per, r, ph in self.planets:
            pts = np.array([self.proj(a * math.cos(q), a * math.sin(q)) for q in th], np.int32)
            col = (110, 200, 255) if name == "venus" else (170, 170, 170)
            cv2.polylines(ov, [pts], True, col, 2, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.5, 0)
        days = t * self.days_per_sec
        bodies = []
        for name, a, per, r, ph in self.planets:
            q = ph + TAU * days / per
            x, y = a * math.cos(q), a * math.sin(q)
            bodies.append((y, name, x, r))
        bodies.append((0.0, "sun", 0, 0))
        for y, name, x, r in sorted(bodies):
            if name == "sun":
                glow(f, 960, 560, 70, (110, 200, 255), 1.0)
                cv2.circle(f, (960, 560), 38, (225, 250, 255), -1, cv2.LINE_AA)
                glow(f, 960, 560, 30, (200, 240, 255), 0.6)
                continue
            sx, sy = self.proj(x, y)
            # light comes from the sun direction (screen space approx)
            lx, ly = 960 - sx, -(560 - sy) * -1
            L = np.array([lx, -(560 - sy) * -1 if False else (sy - 560), 0.0])
            L = np.array([960 - sx, sy - 560, 30.0])
            n = np.linalg.norm(L)
            light = (L[0] / n, L[1] / n, max(L[2] / n, 0.15))
            sph = Sphere(r, light=light, halo=0.25 if name != "mercury" else 0.05, atm_k=0.9 if name != "mercury" else 0.0,
                         atm=(150, 200, 255) if name == "earth" else (240, 200, 140))
            sph.composite(f, sx, sy, self.tex[name], t * 0.05)
            if name == "venus":
                cv2.circle(f, (int(sx), int(sy)), int(r * 1.9), (120, 210, 255), 2, cv2.LINE_AA)
        return camera(f, 1.04 - 0.04 * p)

    def hud(self, t, p):
        return f"{int(t * self.days_per_sec)} Earth days"

    def labels(self, t):
        out = []
        days = t * self.days_per_sec
        for name, a, per, r, ph in self.planets:
            q = ph + TAU * days / per
            sx, sy = self.proj(a * math.cos(q), a * math.sin(q))
            out.append((name.capitalize(), int(sx), int(sy + r + 22)))
        out.append(("Sun", 960, 560 + 68))
        return out


class Twins:
    def __init__(self, dur, **_):
        self.v = Sphere(300, light=(-0.4, 0.25, 0.88))
        self.e = Sphere(316, light=(-0.4, 0.25, 0.88), atm=(130, 180, 255), atm_k=1.2)

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.v.composite(f, 560, 450, texture("venus_clouds"), t * 0.004)
        self.e.composite(f, 1360, 450, texture("earth"), 0.3 + t * 0.006)
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [("VENUS", 560, 820), ("EARTH", 1360, 820)]


class Impact:
    def __init__(self, dur, **_):
        self.big = Sphere(300, light=(-0.6, 0.3, 0.75), atm=(255, 140, 60), atm_k=0.8)
        self.small = Sphere(55, light=(0.2, 0.3, 0.93), atm_k=0.0, halo=0.02)
        r = np.random.default_rng(5)
        n = 260
        self.deb_ang = r.normal(-2.4, 0.55, n)
        self.deb_spd = r.uniform(80, 520, n)
        self.deb_sz = r.uniform(1.5, 5, n)
        self.hit = 0.42

    def frame(self, t, p):
        f = space_bg(t, (2, 1))
        cx, cy = 1150, 580
        hx, hy = cx - 300 * 0.78, cy - 300 * 0.62
        spin = 0.05 * t if p < self.hit else 0.05 * self.hit * 20 - 0.03 * (t - self.hit * 20)
        self.big.composite(f, cx, cy, texture("molten"), spin)
        if p < self.hit:
            q = ease(p / self.hit)
            sx = -150 + (hx + 30 - (-150)) * q
            sy = -120 + (hy + 20 - (-120)) * q
            self.small.composite(f, sx, sy, texture("rock_small"), t * 0.1)
        else:
            dt = (p - self.hit) * 20  # seconds-ish after impact
            k = math.exp(-dt * 1.2)
            glow(f, hx, hy, 160 + 120 * dt, (180, 230, 255), 1.6 * k)
            glow(f, hx, hy, 90, (40, 120, 255), 0.9 * math.exp(-dt * 0.25))
            ov = np.zeros_like(f)
            for a, s, z in zip(self.deb_ang, self.deb_spd, self.deb_sz):
                x = hx + math.cos(a) * s * dt
                y = hy + math.sin(a) * s * dt + 10 * dt * dt
                cv2.circle(ov, (int(x), int(y)), int(z), (60, 150, 255), -1, cv2.LINE_AA)
            f = cv2.addWeighted(f, 1, ov, max(0.0, 1 - dt / 8), 0)
        shake = 0 if p < self.hit else 14 * math.exp(-(p - self.hit) * 40) * math.sin(t * 60)
        return camera(f, 1.0 + 0.05 * p, shake, shake * 0.6)


class Superrotation:
    def __init__(self, dur, **_):
        self.sph = Sphere(380, light=(-0.4, 0.3, 0.86), incl=0.25)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 560
        self.sph.composite(f, cx, cy, texture("venus_clouds"), -t * 0.06)
        ov = np.zeros_like(f)
        for k, (ry, off) in enumerate([(0.16, 0), (0.3, 0.5)]):
            for j in range(6):
                a0 = (j / 6 + t * 0.12 + off) % 1
                st, en = int(200 + a0 * 140), int(200 + a0 * 140 + 26)
                cv2.ellipse(ov, (cx, cy + int((k - 0.5) * 80)), (470, int(470 * ry)), 0, st, en, (140, 220, 255), 4, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.8, 0)
        return camera(f, 1.0 + 0.05 * p)


class OceanVenus:
    def __init__(self, dur, **_):
        self.sph = Sphere(420, light=(-0.5, 0.3, 0.81), atm=(130, 180, 255), atm_k=1.2, incl=0.3)

    def frame(self, t, p):
        f = space_bg(t, (3, 1))
        self.sph.composite(f, 1050, 560, texture("venus_ocean"), t * 0.005)
        return camera(f, 1.0 + 0.06 * p)


class Greenhouse:
    def __init__(self, dur, **_):
        self.a = Sphere(420, light=(-0.5, 0.3, 0.81), atm=(130, 180, 255), atm_k=1.2, incl=0.3)
        self.b = Sphere(420, light=(-0.5, 0.3, 0.81), atm=(240, 200, 140), atm_k=1.0, incl=0.3)

    def frame(self, t, p):
        f = space_bg(t, (3, 1))
        m = smoothstep(0.1, 0.85, np.float32(p)).item()
        ra, aa = self.a.layer(texture("venus_ocean"), 0.11 + t * 0.005)
        rb, ab = self.b.layer(texture("venus_clouds"), 0.11 + t * 0.005)
        add_layer(f, ra * (1 - m) + rb * m, aa, 1050, 560)
        if 0.2 < p < 0.9:
            glow(f, 1050, 560, 380, (90, 160, 230), 0.25 * math.sin((p - 0.2) / 0.7 * math.pi))
        return camera(f, 1.06 - 0.06 * p)


class RadarMap:
    def __init__(self, dur, **_):
        self.sph = Sphere(420, light=(-0.2, 0.25, 0.95), incl=0.2, atm_k=0.3)
        self.tex = texture("venus_radar")

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        sweep = 0.05 + 0.95 * min(1, p / 0.85)

        def reveal(col, u, v):
            uu = (u - 0.0) % 1.0
            shown = uu < sweep
            edge = np.abs(uu - sweep) < 0.004
            dark = col * 0.08
            grid = ((np.abs((u * 36) % 1 - 0.5) > 0.47) | (np.abs((v * 18) % 1 - 0.5) > 0.47))
            dark[grid] = (90, 70, 40)
            out = np.where(shown[..., None], col, dark)
            out[edge] = (170, 240, 255)
            return out
        self.sph.composite(f, 960, 560, self.tex, sweep - 0.08, extra=reveal)
        return camera(f, 1.0 + 0.05 * p)


# ------------------------------------------------------------------ surface scenes
_terrains = {}


def terrain(kind):
    if kind not in _terrains:
        if kind == "volcano":
            tr = gfx.Terrain(seed=51, kind="hills")
            tr.add_volcano(512, 160, radius=230, height=260)
        else:
            tr = gfx.Terrain(seed=41, kind="plains")
        _terrains[kind] = tr
    return _terrains[kind]


VENUS_FOG = (70, 145, 215)       # BGR orange haze
VENUS_SKY_TOP = (40, 95, 170)
VENUS_SKY_HOR = (95, 170, 232)


def shimmer(img, t, amp=1.6):
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h:4, 0:w:4].astype(np.float32)
    dx = amp * np.sin(ys * 0.045 + t * 6.0) * np.sin(xs * 0.01 + t * 2)
    dx = cv2.resize(dx, (w, h))
    mx = (np.arange(w, dtype=np.float32)[None, :] + dx).astype(np.float32)
    my = np.broadcast_to(np.arange(h, dtype=np.float32)[:, None], (h, w)).astype(np.float32)
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


class Surface:
    """Variants: plains walk (surface), heat (thermo), sunrise in the west."""

    def __init__(self, dur, variant="surface", **_):
        self.v = variant
        self.tr = terrain("plains")

    def frame(self, t, p):
        if self.v == "sunrise":
            sy = 0.56 - 0.2 * ease(p)
            img = self.tr.render(300, 700, math.pi + 0.15 * p - 0.1, cam_alt=12, pitch=0.02,
                                 fog_col=VENUS_FOG, sky_top=VENUS_SKY_TOP, sky_hor=VENUS_SKY_HOR,
                                 sun=(0.3, sy, 0.05, (120, 200, 255)))
            return img
        if self.v == "thermo":
            img = self.tr.render(500 + t * 2.0, 300, 0.4, cam_alt=9, pitch=-0.02, fog_col=(60, 130, 215),
                                 sky_top=(30, 80, 170), sky_hor=(80, 150, 235))
            return shimmer(img, t, 2.2)
        img = self.tr.render(100 + t * 1.2, 100 + t * 0.5, 0.35 + 0.05 * math.sin(t * 0.1), cam_alt=4.5, pitch=-0.06,
                             fog_col=VENUS_FOG, sky_top=VENUS_SKY_TOP, sky_hor=VENUS_SKY_HOR)
        return shimmer(img, t, 1.0)


class Volcano:
    def __init__(self, dur, **_):
        self.tr = terrain("volcano")
        self.dur = dur

    def frame(self, t, p):
        # camera approaches the volcano placed at (512,160) from the south
        cy = 160 + 900 - 260 * ease(p)
        img = self.tr.render(512 + 40 * math.sin(p * 2), cy, -math.pi / 2, cam_alt=40 + 20 * p, pitch=0.06,
                             fog_col=(60, 115, 190), fog_dist=650, sky_top=(30, 60, 120), sky_hor=(70, 130, 210))
        # glow above the crater
        glow(img, 960, 400, 120, (30, 90, 255), 0.25 + 0.05 * math.sin(t * 2.3))
        return shimmer(img, t, 1.0)


class DeepSea:
    def __init__(self, dur, **_):
        r = np.random.default_rng(9)
        n = 500
        self.px, self.py = r.uniform(0, W, n), r.uniform(0, H, n)
        self.pz = r.uniform(0.3, 1.0, n)
        rays = np.zeros((H, W), np.float32)
        for i in range(14):
            x = r.uniform(-200, W + 200)
            pts = np.array([[x - 30, 0], [x + 30, 0], [x + 260 + r.uniform(-80, 80), H], [x + 120, H]], np.int32)
            cv2.fillPoly(rays, [pts], r.uniform(0.2, 0.6))
        self.rays = cv2.GaussianBlur(rays, (0, 0), 25)

    def frame(self, t, p):
        d = ease(min(1, p / 0.9))
        top = np.array([200, 150, 40], np.float32) * (1 - d) + np.array([60, 25, 5], np.float32) * d
        bot = np.array([120, 70, 10], np.float32) * (1 - d) + np.array([10, 4, 0], np.float32) * d
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        img = top * (1 - g) + bot * g
        img = np.broadcast_to(img, (H, W, 3)).copy()
        img += self.rays[..., None] * np.array([120, 110, 60], np.float32) * (1 - d) ** 2
        img = np.clip(img, 0, 255).astype(np.uint8)
        ov = np.zeros_like(img)
        for x, y, z in zip(self.px, self.py, self.pz):
            yy = (y - t * 60 * z) % H
            xx = x + 8 * math.sin(t * 0.5 + y)
            cv2.circle(ov, (int(xx), int(yy)), max(1, int(2.5 * z)), (200, 220, 230), -1, cv2.LINE_AA)
        img = cv2.addWeighted(img, 1, ov, 0.35, 0)
        return img

    def hud(self, t, p):
        d = ease(min(1, p / 0.9))
        m = int(930 * d)
        return f"Depth {m} m   ·   {1 + m / 10.1:.0f}× surface pressure"


class Descent:
    def __init__(self, dur, **_):
        n = gfx.fbm(512, 1024, 2.0, 61, ax=1.0, ay=2.0)
        self.cloud = cv2.resize(n, (2048, 1080))
        n2 = gfx.fbm(512, 1024, 2.0, 62)
        self.cloud2 = cv2.resize(n2, (2048, 1080))

    def frame(self, t, p):
        dark = 1 - 0.45 * p
        base = np.array([150, 205, 240], np.float32) * dark
        deep = np.array([60, 120, 200], np.float32) * dark
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        img = np.broadcast_to(base * (1 - g) + deep * g, (H, W, 3)).copy()
        for k, (c, spd, a) in enumerate([(self.cloud2, 40, 0.5), (self.cloud, 110, 0.75)]):
            off = int(t * spd) % H
            layer = np.roll(c, -off, axis=0)[:, 40:40 + W]
            al = smoothstep(0.45, 0.8, layer)[..., None] * a * (1 - 0.5 * p)
            img = img * (1 - al) + np.array([235, 245, 252], np.float32) * dark * al
        img = np.clip(img, 0, 255).astype(np.uint8)
        # lander + parachute
        cx = 960 + 40 * math.sin(t * 0.7)
        cy = 600 + 12 * math.sin(t * 1.3)
        sway = 4 * math.sin(t * 0.7)
        ov = img.copy()
        chute_c, chute_y = (int(cx + sway * 3), int(cy - 260))
        for i in range(-3, 4):
            cv2.line(ov, (int(cx), int(cy - 40)), (chute_c + i * 38, chute_y + 10), (60, 60, 70), 2, cv2.LINE_AA)
        cv2.ellipse(ov, (chute_c, chute_y), (150, 70), 0, 180, 360, (40, 90, 230), -1, cv2.LINE_AA)
        for i in range(-2, 3):
            cv2.ellipse(ov, (chute_c, chute_y), (int(abs(i) * 30 + 1), 70), 0, 180, 360, (230, 235, 240), 3, cv2.LINE_AA)
        cv2.ellipse(ov, (int(cx), int(cy + 10)), (95, 22), 0, 0, 360, (90, 95, 105), -1, cv2.LINE_AA)
        body = np.zeros((120, 120, 3), np.float32)
        yy, xx = np.mgrid[0:120, 0:120].astype(np.float32)
        d = np.sqrt((xx - 60) ** 2 + (yy - 60) ** 2) / 55
        nz = np.sqrt(np.clip(1 - d * d, 0, 1))
        sh = np.clip(0.3 + 0.7 * ((-(xx - 60) * 0.5 - (yy - 60) * 0.6) / 55 + nz * 0.6), 0.1, 1.2)
        body = (np.array([175, 185, 195], np.float32) * sh[..., None])
        a = np.clip((1 - d) * 55, 0, 1)
        add_layer(ov, body * a[..., None], a, cx, cy - 20)
        img = ov
        return img


class EveningStar:
    def __init__(self, dur, **_):
        r = np.random.default_rng(71)
        x = np.arange(W)
        def ridge(seed, amp, base, rough):
            n = gfx.fbm(64, 2048, rough, seed)[32][:W]
            return (base - amp * n).astype(np.int32)
        self.r1 = ridge(72, 140, 1010, 2.2)
        self.r2 = ridge(73, 90, 1080, 2.6)

    def frame(self, t, p):
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        top = np.array([60, 18, 8], np.float32)
        mid = np.array([130, 60, 40], np.float32)
        hor = np.array([90, 150, 245], np.float32)
        c = np.where((g < 0.6)[..., None], top[None] * (1 - g / 0.6)[..., None] + mid[None] * (g / 0.6)[..., None],
                     mid[None] * (1 - (g - 0.6) / 0.4)[..., None] + hor[None] * ((g - 0.6) / 0.4)[..., None])
        img = np.broadcast_to(c, (H, W, 3)).astype(np.float32)
        stars = space_bg(0, (0, 0)).astype(np.float32) * (0.15 + 0.5 * p) * (1 - g[..., None]) ** 2
        img = np.clip(img + stars, 0, 255).astype(np.uint8)
        vx, vy = 1240, 300 + int(30 * p)
        tw = 1 + 0.08 * math.sin(t * 7) + 0.05 * math.sin(t * 13)
        glow(img, vx, vy, 26 * tw, (230, 245, 255), 0.9)
        cv2.circle(img, (vx, vy), 5, (255, 255, 255), -1, cv2.LINE_AA)
        mask = np.zeros((H, W), np.uint8)
        for xs, ys, col in [(np.arange(W), self.r1, (40, 22, 18)), (np.arange(W), self.r2, (14, 8, 6))]:
            pts = np.vstack([np.c_[xs, ys], [[W, H], [0, H]]]).astype(np.int32)
            cv2.fillPoly(img, [pts], col, cv2.LINE_AA)
        return camera(img, 1.02 + 0.03 * p)


class Atmosphere:
    def __init__(self, dur, **_):
        n = gfx.fbm(256, 2048, 2.4, 81, ax=2, ay=1)
        self.cl = n

    def frame(self, t, p):
        img = np.zeros((H, W, 3), np.float32)
        ground = 930
        top = 140
        ys = np.arange(H, dtype=np.float32)[:, None]
        alt = (ground - ys) / (ground - top) * 80  # km
        dens = np.exp(-np.clip(alt, 0, None) / 16.0)
        col = np.array([60, 140, 230], np.float32)
        img = np.broadcast_to(dens[..., None] * col, (H, W, 3)).copy()
        sp = space_bg(t, (2, 0)).astype(np.float32)
        img = img + sp * (1 - np.clip(dens * 4, 0, 1))[..., None]
        # cloud deck 45-70 km
        y70, y45 = ground - 70 / 80 * (ground - top), ground - 45 / 80 * (ground - top)
        off = int(t * 25) % 2048
        band = np.roll(self.cl, -off, axis=1)[:, :W]
        band = cv2.resize(band, (W, int(y45 - y70)))
        a = smoothstep(0.3, 0.75, band)[..., None] * 0.9
        y0 = int(y70)
        seg = img[y0:y0 + band.shape[0]]
        img[y0:y0 + band.shape[0]] = seg * (1 - a) + np.array([150, 215, 240], np.float32) * a
        img[ground:] = np.array([30, 55, 90], np.float32)
        img = np.clip(img, 0, 255).astype(np.uint8)
        for km in (0, 20, 40, 60, 80):
            y = int(ground - km / 80 * (ground - top))
            cv2.line(img, (110, y), (140, y), (230, 230, 230), 2, cv2.LINE_AA)
        cv2.line(img, (140, top), (140, ground), (230, 230, 230), 2, cv2.LINE_AA)
        return img

    def labels(self, t):
        ground, top = 930, 140
        out = [(f"{km} km", 60, int(930 - km / 80 * (930 - 140)) + 8) for km in (0, 20, 40, 60, 80)]
        out += [("Sulfuric acid clouds (about 45–70 km)", 1130, int(ground - 57 / 80 * (ground - top)) + 10)]
        return out


class Flyby:
    def __init__(self, dur, **_):
        self.sph = Sphere(430, light=(-0.6, 0.35, 0.72), incl=0.25)

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.sph.composite(f, 1380, 600, texture("venus_clouds"), t * 0.004)
        x = -150 + 1250 * p
        y = 260 + 120 * p
        draw_probe(f, x, y, 0.9, t)
        return f


def draw_probe(f, x, y, s, t):
    x, y = int(x), int(y)
    ov = f.copy()
    # solar panels
    for side in (-1, 1):
        x0 = x + side * int(40 * s)
        x1 = x + side * int(170 * s)
        pts = np.array([[x0, y - int(22 * s)], [x1, y - int(30 * s)], [x1, y + int(30 * s)], [x0, y + int(22 * s)]], np.int32)
        cv2.fillPoly(ov, [pts], (90, 45, 25), cv2.LINE_AA)
        for k in range(1, 5):
            xx = x0 + (x1 - x0) * k // 5
            cv2.line(ov, (xx, y - int(28 * s)), (xx, y + int(28 * s)), (150, 110, 70), 1, cv2.LINE_AA)
        cv2.polylines(ov, [pts], True, (190, 170, 150), 1, cv2.LINE_AA)
    hexa = np.array([[x + int(42 * s * math.cos(a)), y + int(42 * s * math.sin(a))] for a in np.linspace(0, TAU, 7)[:-1]], np.int32)
    cv2.fillPoly(ov, [hexa], (120, 160, 185), cv2.LINE_AA)
    cv2.fillPoly(ov, [hexa[:3]], (190, 215, 230), cv2.LINE_AA)
    cv2.line(ov, (x, y - int(40 * s)), (x, y - int(120 * s)), (210, 210, 210), 2, cv2.LINE_AA)
    cv2.ellipse(ov, (x + int(18 * s), y + int(62 * s)), (int(40 * s), int(14 * s)), 20, 0, 360, (225, 225, 230), -1, cv2.LINE_AA)
    f[:] = ov


class CloudCity:
    def __init__(self, dur, **_):
        self.sea = gfx.CloudSea()

    def frame(self, t, p):
        img = self.sea.render(t, horizon=0.42, speed=8.0, sky_top=(170, 200, 230), sky_hor=(195, 230, 248))
        glow(img, 1500, 140, 220, (150, 210, 255), 0.35)
        for (bx, by, sc, ph) in [(560, 430, 0.45, 1.3), (1220, 470, 1.0, 0.0)]:
            by = by + 10 * math.sin(t * 0.5 + ph)
            draw_balloon(img, bx + 6 * t * (0.3 if sc < 1 else 0.6), by, sc)
        return camera(img, 1.0 + 0.04 * p)


def draw_balloon(f, cx, cy, s):
    rx, ry = int(230 * s), int(130 * s)
    size = 2 * max(rx, ry) + 8
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    nx, ny = (xx - size / 2) / rx, (yy - size / 2) / ry
    r2 = nx * nx + ny * ny
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    sh = np.clip(0.25 + 0.8 * (nz * 0.7 - ny * 0.45 + nx * 0.2), 0.1, 1.15)
    col = np.array([225, 230, 235], np.float32) * sh[..., None]
    rib = (np.abs(np.sin(nx * 7)) < 0.06) & (r2 < 1)
    col[rib] *= 0.8
    a = np.clip((1 - np.sqrt(r2)) * min(rx, ry) + 0.5, 0, 1)
    add_layer(f, col * a[..., None], a, cx, cy)
    gx, gy = int(cx), int(cy + ry + 40 * s)
    for dx in (-60, 0, 60):
        cv2.line(f, (int(cx + dx * s * 1.6), int(cy + ry * 0.8)), (gx + int(dx * s * 0.6), gy - int(14 * s)), (90, 90, 100), max(1, int(2 * s)), cv2.LINE_AA)
    cv2.rectangle(f, (gx - int(70 * s), gy - int(16 * s)), (gx + int(70 * s), gy + int(22 * s)), (70, 75, 85), -1, cv2.LINE_AA)
    for k in range(5):
        wx = gx - int(55 * s) + int(k * 27 * s)
        cv2.rectangle(f, (wx, gy - int(6 * s)), (wx + int(14 * s), gy + int(8 * s)), (150, 220, 255), -1)


def make(visual, dur, occurrence):
    if visual == "venus_closeup":
        return VenusCloseup(dur, variant=[0, 1, 2][min(occurrence, 2)])
    table = {
        "venus_space": VenusSpace, "venus_spin": VenusSpin, "orbits": Orbits, "twins": Twins, "impact": Impact,
        "superrotation": Superrotation, "ocean_venus": OceanVenus, "greenhouse": Greenhouse, "radar_map": RadarMap,
        "volcano": Volcano, "deep_sea": DeepSea, "descent": Descent, "evening_star": EveningStar,
        "atmosphere": Atmosphere, "flyby": Flyby, "cloud_city": CloudCity,
    }
    if visual == "sunrise_west":
        return Surface(dur, variant="sunrise")
    if visual == "thermo":
        return Surface(dur, variant="thermo")
    if visual == "surface":
        return Surface(dur, variant="surface")
    return table[visual](dur, variant=occurrence) if visual == "orbits" else table[visual](dur)
