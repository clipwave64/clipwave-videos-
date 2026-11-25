"""Scene library for the Saturn long-form video. Every visual is generated in code (no downloaded footage)."""
import math
import numpy as np
import cv2
import gfx
from gfx import W, H, Sphere, texture, space_bg, add_layer, glow, smoothstep, fbm, ramp
from scenes import ease, camera, draw_probe, TAU

SAT_ATM = (240, 215, 170)   # RGB rim colour
OBLATE = 0.90               # polar / equatorial radius

# ring radial profile in Saturn radii: (r0, r1, opacity, rgb)
RINGS = [(1.11, 1.24, 0.06, (150, 135, 120)),   # D
         (1.24, 1.53, 0.28, (165, 148, 125)),   # C
         (1.53, 1.95, 0.92, (232, 214, 182)),   # B
         (1.95, 2.03, 0.07, (120, 110, 100)),   # Cassini Division
         (2.03, 2.27, 0.70, (215, 200, 175)),   # A
         (2.322, 2.330, 0.55, (220, 215, 205))]  # F

_tex = {}


def _store(name, t):
    t = np.clip(t, 0, 255).astype(np.uint8)[..., ::-1].copy()
    _tex[name] = t
    return t


def sat_tex(storm=0.0):
    """Procedural Saturn map (BGR): soft butterscotch bands, blue-grey north, hexagon outline near the pole.
    storm 0..1 = a Great White Spot spreading along the northern band."""
    key = f"sat{round(storm, 2)}"
    if key in _tex:
        return _tex[key]
    th, tw = 1024, 2048
    v = np.linspace(0, 1, th, dtype=np.float32)[:, None]
    u = np.linspace(0, 1, tw, dtype=np.float32)[None, :]
    lat = (0.5 - v) * 180.0
    turb = fbm(th, tw, 2.4, 501, ax=7.0, ay=1.0)
    fine = fbm(th, tw, 1.6, 502, ax=10.0, ay=1.0)
    latw = lat + 2.0 * (turb - 0.5)
    band = 0.5 + 0.30 * np.cos(np.radians(latw) * 11.0) + 0.14 * np.cos(np.radians(latw) * 29.0 + 0.7)
    x = 0.7 * band + 0.2 * fine + 0.1 * turb
    t = ramp(x, [(0, (165, 128, 82)), (0.35, (200, 165, 112)), (0.6, (226, 200, 150)), (0.85, (240, 225, 188)), (1, (248, 240, 215))])
    eq = smoothstep(14, 2, np.abs(lat))
    t = t * (1 - 0.3 * eq[..., None]) + np.array([245, 232, 200], np.float32) * 0.3 * eq[..., None]
    north = smoothstep(50, 75, latw)
    t = t * (1 - 0.45 * north[..., None]) + np.array([170, 175, 165], np.float32) * 0.45 * north[..., None]
    south = smoothstep(-55, -80, latw)
    t = t * (1 - 0.35 * south[..., None]) + np.array([185, 165, 135], np.float32) * 0.35 * south[..., None]
    # hexagon edge at ~77N: radius in "polar distance" varies with longitude as a hexagon
    lon = u * TAU
    seg = (lon % (TAU / 6)) - TAU / 12
    hexr = 13.0 * math.cos(TAU / 12) / np.cos(seg)
    pd = 90 - lat
    edge = np.exp(-((pd - hexr) / 0.9) ** 2)
    t = t * (1 - 0.35 * edge[..., None]) + np.array([120, 130, 140], np.float32) * 0.35 * edge[..., None]
    if storm > 0:
        c_u, c_lat = 0.35, 38.0
        du = ((u - c_u + 0.5) % 1) - 0.5
        span = 0.04 + 0.96 * storm
        along = smoothstep(span / 2, span / 2 - 0.03, np.abs(du)) if span < 1 else np.ones_like(du)
        head = np.exp(-((du + span / 2 - 0.02) / 0.02) ** 2 - ((lat - c_lat) / 3.5) ** 2)
        wob = np.sin(du * 90 + fine * 6) * 1.6
        bandm = np.exp(-((lat - c_lat - wob) / (2.2 + 2.5 * storm)) ** 2) * along
        white = np.clip(bandm * (0.55 + 0.45 * fine) + head, 0, 1)
        t = t * (1 - white[..., None]) + np.array([252, 250, 244], np.float32) * white[..., None]
    t = cv2.GaussianBlur(t, (0, 0), 0.8)
    return _store(key, t)


def moon_tex(name):
    if name in _tex:
        return _tex[name]
    th, tw = 1024, 2048
    a = fbm(th, tw, 2.1, 611 + len(name))
    b = fbm(th, tw, 1.6, 621 + len(name))
    r = np.random.default_rng(631 + len(name))
    v = np.linspace(0, 1, th, dtype=np.float32)[:, None]
    u = np.linspace(0, 1, tw, dtype=np.float32)[None, :]
    if name == "titan":
        band = 0.5 + 0.5 * np.sin((0.5 - v) * 6)
        t = ramp(0.55 * a + 0.25 * b + 0.2 * band, [(0, (175, 110, 40)), (0.5, (215, 150, 60)), (1, (240, 190, 100))])
        t = np.broadcast_to(t, (th, tw, 3)).copy()
    elif name == "enceladus":
        t = ramp(0.6 * a + 0.4 * b, [(0, (205, 215, 222)), (0.6, (235, 240, 245)), (1, (252, 253, 255))])
        img = t.copy()
        for _ in range(80):
            cx, cy, rad = int(r.uniform(0, tw)), int(r.uniform(80, th * 0.6)), int(r.uniform(3, 12))
            cv2.circle(img, (cx, cy), rad, (200, 205, 210), 2, cv2.LINE_AA)
        t = cv2.GaussianBlur(img, (0, 0), 1.0)
    elif name == "mimas":
        t = ramp(a, [(0, (150, 148, 145)), (1, (220, 218, 214))])
        img = t.copy()
        for _ in range(500):
            cx, cy, rad = int(r.uniform(0, tw)), int(r.uniform(30, th - 30)), int(r.uniform(2, 9) ** 1.2)
            cv2.circle(img, (cx, cy), rad, (120, 118, 115), 2, cv2.LINE_AA)
        # Herschel crater (big, with central peak) at u=0.5, slightly north
        cx, cy = int(tw * 0.5), int(th * 0.47)
        cv2.ellipse(img, (cx, cy), (190, 160), 0, 0, 360, (110, 108, 105), -1, cv2.LINE_AA)
        cv2.ellipse(img, (cx, cy), (190, 160), 0, 0, 360, (235, 233, 230), 12, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 26, (225, 222, 218), -1, cv2.LINE_AA)
        t = cv2.GaussianBlur(img, (0, 0), 2.0)
    elif name == "iapetus":
        dark = smoothstep(0.3, 0.2, np.abs(((u - 0.5 + 0.5) % 1) - 0.5) * (1 + 0.6 * np.abs(0.5 - v) * 2) + 0.05 * (a - 0.5))
        bright = ramp(a, [(0, (205, 200, 192)), (1, (245, 242, 236))])
        darkc = ramp(b, [(0, (35, 25, 18)), (1, (75, 55, 40))])
        t = bright * (1 - dark[..., None]) + darkc * dark[..., None]
        ridge = np.exp(-((v - 0.5) / 0.006) ** 2) * smoothstep(0.35, 0.25, np.abs(((u - 0.5 + 0.5) % 1) - 0.5))
        t = t * (1 - 0.6 * ridge[..., None]) + np.array([150, 130, 110], np.float32) * 0.6 * ridge[..., None]
    else:
        raise KeyError(name)
    return _store(name, t)


# ------------------------------------------------------------------ ringed planet renderer
class Ringed:
    """Saturn (oblate) with its rings, seen from an elevation `B` (radians) above the ring plane."""

    def __init__(self, R, B=0.42, light=(-0.55, 0.3, 0.78), atm_k=0.45):
        self.R, self.B = R, B
        self.sph = Sphere(R, light=light, incl=B, atm=SAT_ATM, atm_k=atm_k)
        self.light = np.array(light, np.float32) / np.linalg.norm(light)
        self._ring = None

    def ring_layer(self, B=None):
        B = self.B if B is None else B
        R = self.R
        sb = max(abs(math.sin(B)), 1e-3)
        hw = int(R * 2.42)
        hh = max(2, int(hw * sb) + 2)
        ys, xs = np.mgrid[-hh:hh, -hw:hw].astype(np.float32)
        xs += 0.5; ys += 0.5
        r = np.sqrt(xs ** 2 + (ys / sb) ** 2) / R
        op = np.zeros_like(r)
        col = np.zeros(r.shape + (3,), np.float32)
        for r0, r1, o, c in RINGS:
            m = smoothstep(r0 - 0.004, r0 + 0.004, r) * smoothstep(r1 + 0.004, r1 - 0.004, r)
            op += m * o
            col += m[..., None] * np.array(c[::-1], np.float32)
        # fine ringlets
        fine = 0.9 + 0.07 * np.sin(r * 140) * np.sin(r * 57 + 1.0) + 0.03 * np.sin(r * 330)
        encke = 1 - 0.85 * np.exp(-((r - 2.214) / 0.0035) ** 2)
        op = np.clip(op * fine * encke, 0, 1)
        shade = 1.0
        k = 0.55 + 0.45 * abs(self.light[2]) + 0.25 * sb
        rgb = col * (op * shade * k)[..., None]
        # thin-ring edge-on glint so a crossing still shows a faint line
        if sb < 0.02:
            line = np.exp(-(ys / 1.2) ** 2) * smoothstep(2.3, 1.2, np.abs(xs) / R) * 0.35
            op = np.maximum(op, line)
            rgb = np.maximum(rgb, line[..., None] * np.array([200, 210, 220], np.float32))
        return rgb, op, hh

    def draw(self, f, cx, cy, tex, lon, B=None, scale=1.0):
        if B is not None and abs(B - self.B) > 1e-4:
            self.sph = Sphere(self.R, light=tuple(self.light), incl=B, atm=SAT_ATM, atm_k=0.45)
            self.B = B
            self._ring = None
        if self._ring is None:
            self._ring = self.ring_layer()
        rgb, op, hh = self._ring
        if scale != 1.0:
            rgb = cv2.resize(rgb, None, fx=scale, fy=scale)
            op = cv2.resize(op, None, fx=scale, fy=scale)
            hh = int(hh * scale)
        h2 = rgb.shape[0] // 2
        # back half of the ring (far side, upper on screen)
        self._paste(f, rgb[:h2], op[:h2], cx, cy - h2 / 2)
        # oblate planet
        prgb, pa = self.sph.layer(tex, lon)
        s = prgb.shape[0]
        nh = max(4, int(s * OBLATE))
        prgb = cv2.resize(prgb, (s, nh)); pa = cv2.resize(pa, (s, nh))
        if scale != 1.0:
            prgb = cv2.resize(prgb, None, fx=scale, fy=scale); pa = cv2.resize(pa, None, fx=scale, fy=scale)
        # ring shadow band on the planet (thin dark ellipse just south of the ring line)
        self._paste_planet(f, prgb, pa, cx, cy)
        # front half (near side, lower on screen) covers the planet
        self._paste(f, rgb[h2:], op[h2:], cx, cy + (rgb.shape[0] - h2) / 2)
        return f

    @staticmethod
    def _paste(f, rgb, a, cx, cy):
        h, w = a.shape
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
        if fx1 <= fx0 or fy1 <= fy0:
            return
        sub = rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
        aa = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0][..., None]
        reg = f[fy0:fy1, fx0:fx1].astype(np.float32)
        f[fy0:fy1, fx0:fx1] = np.clip(reg * (1 - aa) + sub, 0, 255).astype(np.uint8)

    @staticmethod
    def _paste_planet(f, rgb, a, cx, cy):
        h, w = a.shape
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
        if fx1 <= fx0 or fy1 <= fy0:
            return
        sub = rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
        aa = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0][..., None]
        reg = f[fy0:fy1, fx0:fx1].astype(np.float32)
        f[fy0:fy1, fx0:fx1] = np.clip(reg * (1 - aa) + sub, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ scenes
class SaturnCloseup:
    """Variants: 0 intro approach, 1 side drift, 2 low ring angle, 3 slow spin, 4 outro pull-back."""

    def __init__(self, dur, variant=0, **_):
        self.v = variant % 5
        if self.v == 1:
            self.s = Ringed(300, B=0.30, light=(0.65, 0.25, 0.72))
        elif self.v == 2:
            self.s = Ringed(360, B=0.16, light=(-0.6, 0.3, 0.74))
        else:
            self.s = Ringed(330, B=0.42)

    def frame(self, t, p):
        f = space_bg(t, (4, 1.5))
        tex = sat_tex()
        if self.v == 0:
            sc = 0.35 + 0.65 * ease(min(1, p * 1.25))
            self.s.draw(f, 960, 540, tex, 0.3 + t * 0.004, scale=sc)
            return camera(f, 1 + 0.03 * p)
        if self.v == 1:
            self.s.draw(f, 900, 560, tex, 0.2 + t * 0.004)
            return camera(f, 1.0 + 0.08 * p, -30 * p, 0)
        if self.v == 2:
            self.s.draw(f, 960, 560, tex, 0.1 + t * 0.005)
            return camera(f, 1.05 + 0.05 * p)
        if self.v == 4:
            self.s.draw(f, 960, 520, tex, 0.5 + t * 0.004)
            return camera(f, 1.12 - 0.12 * ease(p))
        self.s.draw(f, 960, 540, tex, 0.5 + t * 0.005)
        return camera(f, 1.0 + 0.05 * p)


class SaturnScale:
    def __init__(self, dur, **_):
        self.s = Ringed(250, B=0.35, light=(-0.4, 0.25, 0.88))
        self.e = Sphere(int(250 / 9.45), light=(-0.4, 0.25, 0.88), atm=(130, 180, 255), atm_k=1.2)

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.s.draw(f, 760, 470, sat_tex(), 0.55 + t * 0.005)
        self.e.composite(f, 1640, 490, texture("earth"), 0.3 + t * 0.01)
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [("SATURN", 760, 770), ("EARTH", 1640, 560)]


class SaturnBathtub:
    """Cartoon: Saturn bobbing in a giant tub of water (it's a joke!)."""

    def __init__(self, dur, **_):
        self.s = Ringed(250, B=0.30, light=(-0.5, 0.4, 0.77))

    def frame(self, t, p):
        f = np.zeros((H, W, 3), np.uint8)
        f[:] = (70, 50, 40)
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        f[:] = np.clip(np.array([95, 70, 55], np.float32) * (1 - g) + np.array([45, 35, 30], np.float32) * g, 0, 255).astype(np.uint8)
        x0, x1, rim, bot = 170, 1750, 720, 1060
        wl = 735
        # back inner wall of the tub
        cv2.rectangle(f, (x0 + 30, rim - 40), (x1 - 30, rim + 30), (200, 205, 210), -1, cv2.LINE_AA)
        bob = 10 * math.sin(t * 1.3)
        self.s.draw(f, 960, wl - 95 + bob, sat_tex(), 0.4 + t * 0.004)
        # water surface (semi transparent) with gentle waves
        ov = f.copy()
        xs = np.arange(x0 + 30, x1 - 29, 20)
        top = [(int(x), int(wl + 6 * math.sin(x / 70 + t * 2.0))) for x in xs]
        poly = np.array(top + [(x1 - 30, bot), (x0 + 30, bot)], np.int32)
        cv2.fillPoly(ov, [poly], (210, 150, 70), cv2.LINE_AA)
        f = cv2.addWeighted(f, 0.5, ov, 0.5, 0)
        cv2.polylines(f, [np.array(top, np.int32)], False, (250, 230, 200), 4, cv2.LINE_AA)
        # front wall of the tub
        wall = np.array([(x0, rim + 40), (x1, rim + 40), (x1 - 40, bot - 20), (x0 + 40, bot - 20)], np.int32)
        cv2.fillPoly(f, [wall], (236, 239, 242), cv2.LINE_AA)
        cv2.line(f, (x0, rim + 40), (x1, rim + 40), (255, 255, 255), 16, cv2.LINE_AA)
        for fx in (x0 + 120, x1 - 120):
            cv2.ellipse(f, (fx, bot - 5), (45, 25), 0, 0, 360, (90, 160, 200), -1, cv2.LINE_AA)
        return camera(f, 1.0 + 0.03 * p)

    def hud(self, t, p):
        return "Just a joke! (not to scale)"


class SaturnOrbits:
    def __init__(self, dur, **_):
        self.S, self.tilt = 85, 0.36
        self.planets = [("earth", 1.0, 365.25, 12, 0.4), ("saturn", 9.5, 10759.0, 26, 2.0)]
        self.days_per_sec = (10759 * 1.02) / max(dur, 1)
        self.sat = Sphere(26, light=(0, 0, 1), incl=0.4, atm=SAT_ATM, atm_k=0.5)

    def proj(self, x, y):
        return 960 + x * self.S, 520 + y * self.S * self.tilt

    def frame(self, t, p):
        f = (space_bg(t, (1, 0)) * 0.7).astype(np.uint8)
        ov = np.zeros_like(f)
        th = np.linspace(0, TAU, 360)
        for name, a, per, r, ph in self.planets:
            pts = np.array([self.proj(a * math.cos(q), a * math.sin(q)) for q in th], np.int32)
            cv2.polylines(ov, [pts], True, (110, 190, 230) if name == "saturn" else (170, 170, 170), 2, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.5, 0)
        days = t * self.days_per_sec
        glow(f, 960, 520, 30, (110, 200, 255), 1.0)
        cv2.circle(f, (960, 520), 14, (225, 250, 255), -1, cv2.LINE_AA)
        self._pos = []
        for name, a, per, r, ph in self.planets:
            q = ph + TAU * days / per
            sx, sy = self.proj(a * math.cos(q), a * math.sin(q))
            if name == "earth":
                L = np.array([960 - sx, sy - 520, 30.0]); n = np.linalg.norm(L)
                Sphere(r, light=(L[0] / n, L[1] / n, max(L[2] / n, 0.15)), halo=0.25, atm_k=0.8,
                       atm=(150, 200, 255)).composite(f, sx, sy, texture("earth"), t * 0.05)
            else:
                Ringed(r, B=0.4).draw(f, sx, sy, sat_tex(), t * 0.05)
            self._pos.append((name.capitalize(), int(sx), int(sy + r + 26)))
        return camera(f, 1.03 - 0.03 * p)

    def labels(self, t):
        return getattr(self, "_pos", [])

    def hud(self, t, p):
        return f"{min(29.4, t * self.days_per_sec / 365.25):.1f} Earth years"


class SaturnBands:
    """Flat close-up of the soft cloud bands drifting at different speeds."""

    def __init__(self, dur, **_):
        tex = sat_tex()
        th, tw = tex.shape[:2]
        self.tex = tex
        ys = np.arange(H, dtype=np.float32)
        self.v = (0.33 + ys / H * 0.24) * th
        lat = (0.5 - self.v / th) * 180
        self.speed = (np.cos(np.radians(lat) * 11.0) * 30 + 25 * np.exp(-(lat / 18) ** 2)).astype(np.float32)
        self.xs = np.arange(W, dtype=np.float32)

    def frame(self, t, p):
        th, tw = self.tex.shape[:2]
        mu = (self.xs[None, :] * 0.8 + 300 + self.speed[:, None] * t) % tw
        mv = np.broadcast_to(self.v[:, None], (H, W))
        img = cv2.remap(self.tex, mu.astype(np.float32), mv.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        g = np.linspace(-1, 1, W, dtype=np.float32)[None, :, None]
        img = (img.astype(np.float32) * (1.05 - 0.25 * g * g)).clip(0, 255).astype(np.uint8)
        return camera(img, 1.02 + 0.03 * p)


def _sat_sea(seed=550, pal=None):
    sea = gfx.CloudSea(seed=seed)
    n = fbm(1024, 1024, 2.2, seed + 1, ax=3.0)
    n2 = fbm(1024, 1024, 1.6, seed + 2)
    x = 0.7 * n + 0.3 * n2
    pal = pal or [(0, (165, 128, 80)), (0.45, (210, 180, 130)), (0.7, (235, 220, 185)), (1, (250, 244, 225))]
    sea.tex = ramp(x, pal)[..., ::-1].astype(np.float32).copy()
    return sea


class SaturnDive:
    def __init__(self, dur, **_):
        self.sea = _sat_sea()
        r = np.random.default_rng(560)
        self.flashes = [(r.uniform(1, max(2, dur - 1)), r.uniform(200, 1700), r.uniform(600, 950)) for _ in range(int(dur / 2.0) + 2)]

    def frame(self, t, p):
        img = self.sea.render(t, horizon=0.4, speed=9.0, sky_top=(60, 55, 50), sky_hor=(170, 175, 185))
        for ft, x, y in self.flashes:
            d = t - ft
            if 0 <= d < 0.35:
                k = (1 - d / 0.35) * (0.6 + 0.4 * math.sin(d * 60))
                glow(img, x, y, 120, (255, 235, 210), 1.0 * k)
        return camera(img, 1.0 + 0.04 * p)


class SaturnHexagon:
    """Top-down view of the north pole: a rotating hexagonal jet stream with a central vortex."""

    def __init__(self, dur, **_):
        s = 1000
        self.s = s
        ys, xs = np.mgrid[0:s, 0:s].astype(np.float32)
        dx, dy = (xs - s / 2) / (s / 2), (ys - s / 2) / (s / 2)
        self.d = np.sqrt(dx * dx + dy * dy)
        self.ang = np.arctan2(dy, dx)
        self.n1 = fbm(s, s, 2.2, 570)
        self.n2 = fbm(s, s, 1.8, 571)
        self.dur = dur

    def frame(self, t, p):
        s = self.s
        d, ang = self.d, self.ang
        rot = t * 0.05
        seg = ((ang - rot) % (TAU / 6)) - TAU / 12
        hexr = 0.55 * math.cos(TAU / 12) / np.cos(seg)
        inside = smoothstep(0.02, -0.02, d - hexr)
        jet = np.exp(-((d - hexr) / 0.035) ** 2)
        # swirl texture: sample noise rotated by an angle that grows toward the centre
        sw = (rot * 3 + 0.8 / (d + 0.15))
        cs, sn = np.cos(sw), np.sin(sw)
        xs = (s / 2 + (np.cos(ang) * cs - np.sin(ang) * sn) * d * s / 2 * 0.9).astype(np.float32)
        ys = (s / 2 + (np.sin(ang) * cs + np.cos(ang) * sn) * d * s / 2 * 0.9).astype(np.float32)
        n = cv2.remap(self.n1, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # colour shifts from blue to gold over the scene (seasonal change)
        k = smoothstep(0.35, 0.8, np.float32(p)).item()
        inner_a = np.array([150, 120, 95], np.float32) * (1 - k) + np.array([110, 165, 200], np.float32) * k   # BGR
        inner_b = np.array([215, 190, 165], np.float32) * (1 - k) + np.array([170, 215, 235], np.float32) * k
        outer = ramp(self.n2, [(0, (160, 150, 130)), (1, (215, 205, 180))])[..., ::-1]
        inner = inner_a * (1 - n[..., None]) + inner_b * n[..., None]
        img = outer * (1 - inside[..., None]) + inner * inside[..., None]
        img = img * (1 - 0.45 * jet[..., None]) + np.array([235, 235, 235], np.float32) * 0.45 * jet[..., None]
        eye = smoothstep(0.08, 0.03, d)
        img = img * (1 - eye[..., None]) + np.array([40, 45, 55], np.float32) * eye[..., None]
        img *= (0.55 + 0.45 * (1 - d ** 2))[..., None]
        a = smoothstep(1.0, 0.97, d)[..., None]
        f = space_bg(t, (2, 0))
        x0, y0 = 960 - s // 2, 540 - s // 2
        x0c, y0c = max(0, x0), max(0, y0)
        sub = img[y0c - y0:y0c - y0 + H, x0c - x0:]
        aa = a[y0c - y0:y0c - y0 + H, x0c - x0:]
        hh, ww = sub.shape[:2]
        reg = f[y0c:y0c + hh, x0c:x0c + ww].astype(np.float32)
        f[y0c:y0c + hh, x0c:x0c + ww] = np.clip(reg * (1 - aa) + sub * aa, 0, 255).astype(np.uint8)
        return camera(f, 1.0 + 0.06 * p)

    def hud(self, t, p):
        return "North pole (artist's view)"


class SaturnStorm:
    def __init__(self, dur, **_):
        self.s = Ringed(340, B=0.30, light=(-0.45, 0.3, 0.84))
        self.steps = 12

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        k = round(ease(min(1, p * 1.15)) * self.steps) / self.steps
        self.s.draw(f, 960, 560, sat_tex(k), 0.15 + t * 0.003)
        return camera(f, 1.0 + 0.05 * p)

    def hud(self, t, p):
        return "2010-2011 (artist's view)"


class SaturnInterior:
    LAYERS = [(1.00, (225, 195, 145), "Clouds"), (0.90, (190, 150, 105), "Hydrogen gas turning liquid"),
              (0.62, (120, 85, 110), "Metallic hydrogen"), (0.30, (80, 65, 120), "Fuzzy core of ice and rock")]

    def __init__(self, dur, **_):
        self.R = 420
        r = np.random.default_rng(580)
        self.drops = [(r.uniform(0, TAU), r.uniform(0, 1), r.uniform(0.04, 0.08)) for _ in range(70)]

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy, R = 720, 540, self.R
        ov = f.copy()
        for fr, col, _ in self.LAYERS:
            cv2.ellipse(ov, (cx, cy), (int(R * fr), int(R * fr * OBLATE)), 0, 0, 360, col[::-1], -1, cv2.LINE_AA)
        core = np.zeros_like(f, np.float32)
        cv2.circle(core, (cx, cy), int(R * 0.32), (150, 100, 80), -1, cv2.LINE_AA)
        core = cv2.GaussianBlur(core, (0, 0), 35)
        ov = np.clip(ov.astype(np.float32) * 0.85 + core * 0.45, 0, 255).astype(np.uint8)
        # helium rain: droplets sinking through the hydrogen
        for a, ph, sp in self.drops:
            k = (ph + t * sp) % 1
            rr = R * (0.88 - 0.5 * k)
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a) * OBLATE
            cv2.circle(ov, (int(x), int(y)), 4, (255, 230, 200), -1, cv2.LINE_AA)
        pulse = 0.5 + 0.5 * math.sin(t * 1.5)
        cv2.ellipse(ov, (cx, cy), (int(R * 0.62), int(R * 0.62 * OBLATE)), 0, 0, 360, (int(170 + 70 * pulse), 140, 220), 2, cv2.LINE_AA)
        return camera(ov, 1.0 + 0.04 * p)

    def labels(self, t):
        return [(n, 1500, y) for (_, _, n), y in zip(self.LAYERS, [190, 360, 540, 710])]


class SaturnGalileo:
    """Through a small telescope: a blurry blob with 'ears' that sharpens into a ringed planet."""

    def __init__(self, dur, **_):
        self.s = Ringed(70, B=0.35, light=(0, 0, 1), atm_k=0.2)

    def frame(self, t, p):
        cx, cy, R = 960, 520, 420
        img = np.zeros((H, W, 3), np.uint8)
        self.s.draw(img, cx, cy, sat_tex(), 0.3)
        sharp = ease(max(0, (p - 0.55) / 0.4))
        sig = 1.0 + 16 * (1 - sharp)
        img = cv2.GaussianBlur(img, (0, 0), sig)
        if sharp < 1:
            img = np.clip(img.astype(np.float32) * (1 + 0.8 * (1 - sharp)), 0, 255).astype(np.uint8)
        view = (space_bg(0, (0, 0)) * 0.3).astype(np.uint8)
        view = np.maximum(view, img)
        mask = np.zeros((H, W), np.uint8)
        cv2.circle(mask, (cx, cy), R, 255, -1, cv2.LINE_AA)
        f = np.where(mask[..., None] > 0, view, np.zeros_like(view))
        cv2.circle(f, (cx, cy), R, (60, 60, 70), 6, cv2.LINE_AA)
        self._sharp = sharp
        return f

    def hud(self, t, p):
        return "1610: what Galileo saw" if getattr(self, "_sharp", 0) < 0.5 else "1650s: Huygens' ring"


class SaturnRingFly:
    """Flying just above the ring plane through a field of ice chunks."""

    def __init__(self, dur, **_):
        r = np.random.default_rng(590)
        n = 2600
        self.x = r.uniform(-60, 60, n).astype(np.float32)
        self.z = r.uniform(0, 120, n).astype(np.float32)
        self.y = r.normal(0, 0.25, n).astype(np.float32)
        self.size = (r.random(n) ** 3 * 1.6 + 0.08).astype(np.float32)
        self.shade = r.uniform(0.55, 1.0, n).astype(np.float32)
        self.sat = Sphere(900, light=(-0.4, 0.5, 0.77), incl=0.1, atm=SAT_ATM, atm_k=0.5)

    def frame(self, t, p):
        f = space_bg(t, (1, 0))
        add = self.sat.layer(sat_tex(), 0.4 + t * 0.002)
        add_layer(f, add[0], add[1], 1300, -520)
        cam_h, speed, fov = 2.2 + 0.3 * math.sin(t * 0.3), 3.5, 900
        z = (self.z - t * speed) % 120 + 0.5
        sx = W / 2 + self.x / z * fov
        sy = H * 0.45 + (cam_h - self.y) / z * fov
        rad = self.size / z * fov * 0.5
        order = np.argsort(-z)
        haze = np.exp(-z / 70)
        for i in order:
            if rad[i] < 0.4 or not (-50 < sx[i] < W + 50 and -50 < sy[i] < H + 50):
                continue
            c = self.shade[i] * (0.35 + 0.65 * haze[i])
            col = (int(215 * c), int(225 * c), int(235 * c))
            cv2.circle(f, (int(sx[i]), int(sy[i])), max(1, int(rad[i])), col, -1, cv2.LINE_AA)
            if rad[i] > 6:
                cv2.circle(f, (int(sx[i] - rad[i] * 0.3), int(sy[i] - rad[i] * 0.3)), max(1, int(rad[i] * 0.35)),
                           (250, 252, 255), -1, cv2.LINE_AA)
        return f

    def hud(self, t, p):
        return "Ring particles (artist's view)"


class SaturnRingParts:
    def __init__(self, dur, **_):
        self.s = Ringed(230, B=0.55, light=(-0.45, 0.35, 0.82))

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        self.s.draw(f, 960, 520, sat_tex(), 0.3 + t * 0.004)
        return camera(f, 1.0 + 0.03 * p)

    def labels(self, t):
        R, sb = 230, math.sin(0.55)
        cy = 520
        out = []
        for name, r in (("C", 1.40), ("B", 1.75), ("A", 2.15)):
            out.append((name, int(960 + R * r), int(cy + 18)))
        out.append(("Cassini Division", int(960 - R * 1.99), int(cy + R * 1.99 * sb + 40)))
        out.append(("F ring", int(960 + R * 2.33 * 0.7), int(cy + R * 2.33 * sb * 0.72 + 40)))
        return out


class SaturnRingsEdge:
    """Ring opening angle closes from wide open to exactly edge-on."""

    def __init__(self, dur, **_):
        self.s = Ringed(300, B=0.45)
        self.cache = {}

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        B = 0.45 * (1 - ease(min(1, p * 1.25)))
        Bq = round(B, 3)
        self.s.draw(f, 960, 540, sat_tex(), 0.3 + t * 0.004, B=max(Bq, 0.0005))
        self._deg = math.degrees(B)
        return f

    def hud(self, t, p):
        return f"Ring tilt seen from Earth: {getattr(self, '_deg', 0):.0f}°"


class SaturnRingRain:
    def __init__(self, dur, **_):
        self.s = Ringed(360, B=0.30)
        r = np.random.default_rng(600)
        self.pr = [(r.choice([-1, 1]), r.uniform(1.3, 2.1), r.uniform(0, 1), r.uniform(0.08, 0.16)) for _ in range(140)]

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy, R = 960, 560, 360
        self.s.draw(f, cx, cy, sat_tex(), 0.2 + t * 0.003)
        ov = np.zeros_like(f, np.float32)
        for side, r0, ph, sp in self.pr:
            for tr in range(4):
                k = (ph + t * sp - tr * 0.015) % 1
                # arc from the ring up and over into the planet's mid-northern latitudes
                x = cx + side * R * (r0 + (0.62 - r0) * k)
                y = cy - R * 0.62 * OBLATE * k - math.sin(k * math.pi) * R * 0.45
                cv2.circle(ov, (int(x), int(y)), 3 - tr // 2, (255, 240, 210), -1, cv2.LINE_AA)
        ov = cv2.GaussianBlur(ov, (0, 0), 2.5)
        f = np.clip(f.astype(np.float32) + ov * 1.2, 0, 255).astype(np.uint8)
        return camera(f, 1.0 + 0.05 * p)

    def hud(self, t, p):
        return "Ring rain (artist's view)"


MOONS = [("Mimas", 0.94, 190, 9, "mimas"), ("Enceladus", 1.37, 250, 10, "enceladus"),
         ("Titan", 15.9, 560, 26, "titan"), ("Iapetus", 79.3, 820, 12, "iapetus")]


class SaturnMoons:
    def __init__(self, dur, **_):
        self.s = Ringed(90, B=0.30)
        self.ms = {k: Sphere(r, light=(-0.6, 0.3, 0.74), atm_k=0.0, halo=0.02) for _, _, _, r, k in MOONS}
        self.dur = dur
        r = np.random.default_rng(610)
        self.small = [(r.uniform(300, 900), r.uniform(0, TAU), r.uniform(0.3, 1.5)) for _ in range(90)]

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 520
        ov = np.zeros_like(f)
        for _, _, a, _, _ in MOONS:
            cv2.ellipse(ov, (cx, cy), (a, int(a * 0.3)), 0, 0, 360, (150, 150, 160), 1, cv2.LINE_AA)
        f = cv2.addWeighted(f, 1, ov, 0.4, 0)
        for a, q0, sp in self.small:   # many small irregular moons as dots
            q = q0 + t * 0.02 * sp
            cv2.circle(f, (int(cx + a * math.cos(q)), int(cy + a * 0.3 * math.sin(q))), 2, (200, 200, 205), -1, cv2.LINE_AA)
        days = t / max(self.dur, 1) * 20
        bodies = []
        for name, per, a, r, key in MOONS:
            q = TAU * days / per + len(name)
            bodies.append((a * 0.3 * math.sin(q), name, a * math.cos(q), key, r))
        for y, name, x, key, r in sorted(bodies):
            if y < 0:
                self.ms[key].composite(f, cx + x, cy + y, moon_tex(key), t * 0.05)
        self.s.draw(f, cx, cy, sat_tex(), t * 0.02)
        for y, name, x, key, r in sorted(bodies):
            if y >= 0:
                self.ms[key].composite(f, cx + x, cy + y, moon_tex(key), t * 0.05)
        self._pos = [(name, int(cx + x), int(cy + y + r + 30)) for y, name, x, key, r in bodies if abs(x) > 230 or y > 60]
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return getattr(self, "_pos", [])


class TitanHaze:
    def __init__(self, dur, **_):
        self.sph = Sphere(400, light=(-0.6, 0.3, 0.74), incl=0.15, atm=(255, 170, 70), atm_k=1.6, halo=0.2)
        self.m = Sphere(int(400 * 4880 / 5150), light=(-0.6, 0.3, 0.74), incl=0.1, atm_k=0.0, halo=0.02)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        k = ease(min(1, max(0, (p - 0.35) / 0.3)))
        x = 960 - 380 * k
        self.sph.composite(f, x, 540, moon_tex("titan"), 0.2 + t * 0.004)
        k2 = max(0.0, (k - 0.6) / 0.4)
        if k2 > 0:
            lay = self.m.layer(texture("mercury"), 0.3 + t * 0.004)
            add_layer(f, lay[0] * k2, lay[1] * k2, 1460, 540 + 400 - self.m.R)
        self._k = k
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        out = [("Titan 5,150 km", int(960 - 380 * getattr(self, "_k", 0)), 175)]
        if getattr(self, "_k", 0) > 0.9:
            out.append(("Mercury 4,880 km", 1460, 175))
        return out


class TitanLakes:
    """Low flight over a dark methane sea and orange shores under an orange sky, with drizzle."""

    def __init__(self, dur, **_):
        sea = gfx.CloudSea(seed=620)
        n = fbm(1024, 1024, 2.3, 621)
        d = fbm(1024, 1024, 1.7, 622)
        land = smoothstep(0.7, 0.73, n)
        ground = ramp(d, [(0, (120, 75, 35)), (0.5, (170, 110, 50)), (1, (210, 150, 80))])
        water = ramp(d, [(0, (28, 24, 22)), (1, (55, 45, 38))])
        tex = water * (1 - land[..., None]) + ground * land[..., None]
        sea.tex = tex[..., ::-1].astype(np.float32).copy()
        self.sea = sea
        r = np.random.default_rng(623)
        self.rain = [(r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.2)) for _ in range(220)]

    def frame(self, t, p):
        f = self.sea.render(t, horizon=0.38, speed=6.0, sky_top=(35, 85, 150), sky_hor=(95, 160, 220))
        for x, y, sp in self.rain:
            yy = (y + t * 240 * sp) % H
            cv2.line(f, (int(x), int(yy)), (int(x - 4), int(yy + 22)), (150, 195, 230), 1, cv2.LINE_AA)
        return camera(f, 1.0 + 0.03 * p)

    def hud(self, t, p):
        return "Methane sea (artist's view)"


class HuygensLanding:
    def __init__(self, dur, **_):
        self.sea = _sat_sea(640, [(0, (150, 90, 30)), (0.45, (200, 135, 55)), (0.7, (225, 165, 80)), (1, (240, 195, 120))])

    def frame(self, t, p):
        img = self.sea.render(t, horizon=0.35 - 0.2 * p, speed=4.0, sky_top=(30, 70, 120), sky_hor=(90, 150, 215))
        cx = 960 + 30 * math.sin(t * 0.5)
        cy = 540 + 12 * math.sin(t * 1.1)
        cc, ct = int(cx), int(cy - 240)
        for i in range(-3, 4):
            cv2.line(img, (int(cx), int(cy - 30)), (cc + i * 30, ct + 8), (60, 60, 70), 2, cv2.LINE_AA)
        cv2.ellipse(img, (cc, ct), (120, 55), 0, 180, 360, (60, 140, 235), -1, cv2.LINE_AA)
        for i in (-2, 0, 2):
            cv2.ellipse(img, (cc, ct), (int(abs(i) * 28 + 1), 55), 0, 180, 360, (240, 240, 245), 3, cv2.LINE_AA)
        # Huygens: a shallow cone (heat-shield shaped) disc
        cv2.ellipse(img, (int(cx), int(cy)), (62, 22), 0, 0, 360, (150, 160, 175), -1, cv2.LINE_AA)
        cv2.ellipse(img, (int(cx), int(cy) - 10), (40, 16), 0, 0, 360, (200, 205, 215), -1, cv2.LINE_AA)
        return img

    def hud(self, t, p):
        return f"Altitude about {int(150 * (1 - ease(p)))} km"


class EnceladusGeysers:
    def __init__(self, dur, **_):
        self.sph = Sphere(340, light=(-0.5, 0.1, 0.86), incl=-0.55, atm_k=0.0, halo=0.02)
        r = np.random.default_rng(650)
        self.pn = 420
        self.pv = r.uniform(0.5, 1.0, self.pn)
        self.pa = r.uniform(-0.35, 0.35, self.pn)
        self.pph = r.uniform(0, 1, self.pn)
        self.src = r.uniform(-0.5, 0.5, self.pn)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy, R = 1180, 420, 340
        self.sph.composite(f, cx, cy, moon_tex("enceladus"), 0.2 + t * 0.006)
        for k in range(4):   # tiger stripes
            yy = cy + R * (0.58 + 0.08 * k)
            half = math.sqrt(max(0, R * R - (yy - cy) ** 2)) * 0.6
            pts = [(int(cx - half + j * 2 * half / 20 - 30 + 15 * k), int(yy + 6 * math.sin(j * 0.8 + k))) for j in range(21)]
            cv2.polylines(f, [np.array(pts, np.int32)], False, (170, 140, 100), 4, cv2.LINE_AA)
        ov = np.zeros_like(f, np.float32)
        for v, a, q, s in zip(self.pv, self.pa, self.pph, self.src):
            ang = -math.pi / 2 + s * 0.9      # sources spread across the south polar region (bottom of the disc)
            nx, ny = math.cos(ang), -math.sin(ang)
            bx, by = cx + nx * R * 0.97, cy + ny * R * 0.97
            k = (q + t * 0.22) % 1
            dist = k * 520 * v
            x = bx + nx * dist + a * dist * 0.6
            y = by + ny * dist
            c = 1 - k
            cv2.circle(ov, (int(x), int(y)), 4, (255 * c, 245 * c, 235 * c), -1, cv2.LINE_AA)
        ov = cv2.GaussianBlur(ov, (0, 0), 4)
        f = np.clip(f.astype(np.float32) + ov * 2.6, 0, 255).astype(np.uint8)
        return camera(f, 1.0 + 0.04 * p)

    def labels(self, t):
        return [("Enceladus", 1180, 40)]


class MimasIapetus:
    def __init__(self, dur, **_):
        self.mi = Sphere(300, light=(-0.4, 0.3, 0.87), incl=0.1, atm_k=0.0, halo=0.02)
        self.ia = Sphere(300, light=(-0.4, 0.3, 0.87), incl=0.05, atm_k=0.0, halo=0.02)

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        self.mi.composite(f, 540, 500, moon_tex("mimas"), 0.40 + 0.08 * ease(p))
        self.ia.composite(f, 1380, 500, moon_tex("iapetus"), 0.1 + t * 0.008)
        return camera(f, 1.0 + 0.03 * p)

    def labels(self, t):
        return [("Mimas", 540, 860), ("Iapetus", 1380, 860)]


class SaturnFlyby:
    def __init__(self, dur, **_):
        self.s = Ringed(300, B=0.25, light=(-0.6, 0.35, 0.72))

    def frame(self, t, p):
        f = space_bg(t, (3, 0))
        self.s.draw(f, 1250, 600, sat_tex(), 0.2 + t * 0.004)
        draw_probe(f, -150 + 1250 * p, 200 + 100 * p, 0.8, t)
        return f


class CassiniFinale:
    """Spacecraft weaving through the gap between the cloud tops and the inner rings, then the final plunge."""

    def __init__(self, dur, **_):
        self.s = Ringed(620, B=0.12, light=(-0.5, 0.35, 0.79))

    def frame(self, t, p):
        f = space_bg(t, (2, 0))
        cx, cy = 960, 900
        self.s.draw(f, cx, cy, sat_tex(), 0.3 + t * 0.003)
        R = 620
        if p < 0.75:
            q = (p / 0.75) * 3 % 1
            x = cx - R * 1.6 + q * R * 3.2
            y = cy - R * OBLATE * 1.0 - 60 + 40 * math.sin(q * math.pi)
            draw_probe(f, x, y, 0.38, t)
        else:
            q = (p - 0.75) / 0.25
            x, y = cx + 300 * (1 - q), cy - R * OBLATE - 120 + q * 200
            if q < 0.85:
                draw_probe(f, x, y, 0.38 * (1 - 0.6 * q), t)
            glow(f, x, y, 30 + 40 * q, (180, 220, 255), 0.6 * q)
        return camera(f, 1.0 + 0.04 * p)

    def hud(self, t, p):
        return "Grand Finale, 2017" if p < 0.75 else "September 15, 2017"


class Dragonfly:
    """A rotorcraft flying over Titan's dunes under an orange sky."""

    def __init__(self, dur, **_):
        self.sea = _sat_sea(660, [(0, (95, 60, 25)), (0.45, (150, 100, 45)), (0.7, (185, 130, 65)), (1, (215, 160, 90))])

    def frame(self, t, p):
        img = self.sea.render(t, horizon=0.42, speed=10.0, sky_top=(40, 90, 150), sky_hor=(100, 165, 225))
        cx = 900 + 120 * math.sin(t * 0.25)
        cy = 420 + 20 * math.sin(t * 0.7)
        x, y = int(cx), int(cy)
        cv2.rectangle(img, (x - 110, y - 30), (x + 110, y + 30), (70, 80, 95), -1, cv2.LINE_AA)
        cv2.rectangle(img, (x - 100, y - 24), (x + 100, y - 4), (130, 140, 155), -1, cv2.LINE_AA)
        for sx in (-150, 150):
            for sy in (-55, 45):
                px, py = x + sx, y + sy
                cv2.line(img, (x + sx // 2, y), (px, py), (60, 60, 70), 4, cv2.LINE_AA)
                spin = (t * 25) % TAU
                rx = int(70 * abs(math.cos(spin)) + 20)
                cv2.ellipse(img, (px, py - 12), (rx, 8), 0, 0, 360, (200, 205, 210), 2, cv2.LINE_AA)
        cv2.line(img, (x - 70, y + 30), (x - 90, y + 60), (60, 60, 70), 4, cv2.LINE_AA)
        cv2.line(img, (x + 70, y + 30), (x + 90, y + 60), (60, 60, 70), 4, cv2.LINE_AA)
        return camera(img, 1.0 + 0.03 * p)

    def hud(self, t, p):
        return "Dragonfly on Titan (artist's view)"


TABLE = {
    "saturn_scale": SaturnScale, "saturn_bathtub": SaturnBathtub, "saturn_orbits": SaturnOrbits, "saturn_bands": SaturnBands,
    "saturn_dive": SaturnDive, "saturn_hexagon": SaturnHexagon, "saturn_storm": SaturnStorm, "saturn_interior": SaturnInterior,
    "saturn_galileo": SaturnGalileo, "saturn_ringfly": SaturnRingFly, "saturn_ringparts": SaturnRingParts,
    "saturn_rings_edge": SaturnRingsEdge, "saturn_ring_rain": SaturnRingRain, "saturn_moons": SaturnMoons,
    "titan_haze": TitanHaze, "titan_lakes": TitanLakes, "huygens_landing": HuygensLanding,
    "enceladus_geysers": EnceladusGeysers, "mimas_iapetus": MimasIapetus, "saturn_flyby": SaturnFlyby,
    "cassini_finale": CassiniFinale, "dragonfly": Dragonfly,
}
VARIANT = {"saturn_closeup": SaturnCloseup}
VISUALS = set(TABLE) | set(VARIANT)


def make(visual, dur, occurrence):
    if visual in VARIANT:
        return VARIANT[visual](dur, variant=occurrence if occurrence < 3 else 4)
    return TABLE[visual](dur)
