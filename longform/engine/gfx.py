"""Procedural 3D-ish graphics for ClipWave long-form videos (all original, code-generated)."""
import math
import numpy as np
import cv2

W, H = 1920, 1080
rng_global = np.random.default_rng(7)


# ---------------------------------------------------------------- noise / textures
def fbm(h, w, beta=2.0, seed=0, ax=1.0, ay=1.0):
    """Periodic fractal noise via spectral synthesis, normalized to 0..1."""
    r = np.random.default_rng(seed)
    white = r.standard_normal((h, w))
    ky = np.fft.fftfreq(h)[:, None] * h
    kx = np.fft.rfftfreq(w)[None, :] * w
    k = np.sqrt((kx * ax) ** 2 + (ky * ay) ** 2)
    k[0, 0] = 1e9
    f = np.fft.rfft2(white) / k ** (beta * 0.75)
    n = np.fft.irfft2(f, s=(h, w))
    n -= n.min(); n /= n.max()
    return n.astype(np.float32)


def ramp(x, stops):
    """Map 0..1 array to RGB via list of (pos, (r,g,b))."""
    pos = np.array([s[0] for s in stops], np.float32)
    cols = np.array([s[1] for s in stops], np.float32)
    out = np.empty(x.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(x, pos, cols[:, c])
    return out


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


_tex_cache = {}


def texture(name):
    if name in _tex_cache:
        return _tex_cache[name]
    th, tw = 1024, 2048
    lat = np.linspace(math.pi / 2, -math.pi / 2, th, dtype=np.float32)[:, None]
    if name == "venus_clouds":
        a = fbm(th, tw, 2.3, 1, ax=3.5, ay=1.0)
        b = fbm(th, tw, 1.8, 2, ax=6.0, ay=1.0)
        band = 0.5 + 0.5 * np.sin(lat * 7 + 3 * (a - 0.5))
        x = 0.55 * a + 0.25 * b + 0.2 * band
        x = (x - x.min()) / (x.max() - x.min())
        x = x * (0.75 + 0.25 * np.abs(np.sin(lat)))  # brighter polar collars
        x = np.clip((x - 0.5) * 1.25 + 0.5, 0, 1)
        t = ramp(x, [(0, (120, 86, 45)), (0.35, (184, 140, 82)), (0.6, (226, 196, 140)), (0.85, (243, 228, 190)), (1, (252, 245, 222))])
    elif name == "venus_surface":
        a = fbm(th, tw, 2.1, 3)
        c = fbm(th, tw, 1.6, 4)
        x = 0.7 * a + 0.3 * c
        t = ramp(x, [(0, (60, 34, 18)), (0.4, (120, 70, 35)), (0.6, (165, 100, 50)), (0.8, (200, 135, 70)), (1, (235, 180, 110))])
    elif name == "venus_radar":
        a = fbm(th, tw, 2.0, 5)
        c = fbm(th, tw, 1.3, 6)
        flows = np.abs(fbm(th, tw, 2.6, 7) - 0.5) < 0.012
        x = np.clip(0.55 * a + 0.45 * c, 0, 1) ** 1.4
        x = np.where(flows, x + 0.35, x)
        g = np.clip(x, 0, 1)
        t = ramp(g, [(0, (40, 25, 10)), (0.5, (170, 110, 45)), (1, (255, 210, 140))])
    elif name == "venus_ocean":
        a = fbm(th, tw, 2.2, 8)
        land = smoothstep(0.55, 0.6, a)
        sea = ramp(a, [(0, (8, 30, 80)), (0.55, (25, 80, 140))])
        ground = ramp(a, [(0.55, (90, 110, 60)), (0.75, (140, 120, 80)), (1, (200, 190, 170))])
        t = sea * (1 - land[..., None]) + ground * land[..., None]
        cl = smoothstep(0.55, 0.8, fbm(th, tw, 2.0, 9, ax=2.0))
        t = t * (1 - cl[..., None]) + 245 * cl[..., None]
    elif name == "earth":
        a = fbm(th, tw, 2.3, 10)
        land = smoothstep(0.6, 0.62, a)
        polar = smoothstep(1.15, 1.3, np.abs(lat) + 0.2 * a)
        sea = ramp(a, [(0, (5, 20, 60)), (0.6, (20, 60, 130))])
        ground = ramp(fbm(th, tw, 2.0, 11), [(0, (60, 90, 40)), (0.5, (110, 120, 60)), (1, (170, 140, 95))])
        t = sea * (1 - land[..., None]) + ground * land[..., None]
        t = t * (1 - polar[..., None]) + 240 * polar[..., None]
        cl = smoothstep(0.55, 0.85, fbm(th, tw, 2.0, 12, ax=2.5))
        t = t * (1 - 0.9 * cl[..., None]) + 250 * 0.9 * cl[..., None]
    elif name == "mercury":
        a = fbm(th, tw, 1.9, 13)
        t = ramp(a, [(0, (60, 58, 55)), (1, (170, 165, 158))])
    elif name == "molten":
        a = fbm(th, tw, 2.0, 14)
        cracks = np.abs(fbm(th, tw, 2.4, 15) - 0.5) < 0.01
        t = ramp(a, [(0, (40, 25, 20)), (1, (110, 80, 60))])
        t[cracks] = (255, 120, 30)
    elif name == "rock_small":
        a = fbm(th, tw, 1.8, 16)
        t = ramp(a, [(0, (50, 45, 40)), (1, (140, 125, 110))])
    else:
        raise KeyError(name)
    t = np.clip(t, 0, 255).astype(np.uint8)[..., ::-1].copy()  # store BGR for cv2
    _tex_cache[name] = t
    return t


# ---------------------------------------------------------------- stars
_stars = None


def starfield():
    global _stars
    if _stars is None:
        h, w = H + 300, W + 400
        img = np.zeros((h, w, 3), np.float32)
        r = np.random.default_rng(3)
        n = 2600
        ys, xs = r.integers(0, h, n), r.integers(0, w, n)
        mag = r.power(6, n)[::-1] if False else r.random(n) ** 6
        tint = r.choice([0, 1, 2], n, p=[0.7, 0.18, 0.12])
        cols = np.array([[1, 1, 1], [1, 0.85, 0.7], [0.75, 0.85, 1]], np.float32)
        for y, x, m, ti in zip(ys, xs, mag, tint):
            v = 40 + 215 * m
            img[y, x] += cols[ti] * v
        img = cv2.GaussianBlur(img, (0, 0), 0.7) * 2.2
        big = r.random(60)
        for i in range(60):
            y, x = r.integers(0, h), r.integers(0, w)
            cv2.circle(img, (int(x), int(y)), 1, (255, 255, 255), -1, cv2.LINE_AA)
        neb = fbm(h // 4, w // 4, 2.6, 21)
        neb = cv2.resize(neb, (w, h))
        neb = smoothstep(0.55, 1.0, neb)[..., None] * np.array([40, 22, 30], np.float32)
        img += neb
        _stars = np.clip(img, 0, 255).astype(np.uint8)
    return _stars


def space_bg(t, drift=(6, 2)):
    s = starfield()
    ox = int(200 + drift[0] * t) % 400
    oy = int(150 + drift[1] * t) % 300
    return s[oy:oy + H, ox:ox + W].copy()


# ---------------------------------------------------------------- sphere renderer
class Sphere:
    """Pre-computed geometry for a lit, textured sphere rendered into an RGBA layer."""

    def __init__(self, R, light=(-0.6, 0.25, 0.75), tilt=0.0, incl=0.25, atm=(240, 200, 140), atm_k=1.0,
                 halo=0.12, terminator=0.12, ambient=0.02):
        self.R = R
        pad = int(R * (1 + halo) + 4)
        self.size = 2 * pad
        ys, xs = np.mgrid[0:self.size, 0:self.size].astype(np.float32)
        nx = (xs - pad + 0.5) / R
        ny = -(ys - pad + 0.5) / R
        r2 = nx * nx + ny * ny
        d = np.sqrt(r2)
        inside = r2 < 1
        nz = np.sqrt(np.clip(1 - r2, 0, 1))
        L = np.array(light, np.float32); L /= np.linalg.norm(L)
        ndl = nx * L[0] + ny * L[1] + nz * L[2]
        # body coordinates: rotate by screen tilt, then inclination about x
        ct, st = math.cos(tilt), math.sin(tilt)
        bx = nx * ct - ny * st
        by = nx * st + ny * ct
        ci, si = math.cos(incl), math.sin(incl)
        by2 = by * ci + nz * si
        bz2 = -by * si + nz * ci
        lat = np.arcsin(np.clip(by2, -1, 1))
        lon = np.arctan2(bx, bz2)
        self.u0 = (lon / (2 * math.pi) % 1).astype(np.float32)
        self.v = ((0.5 - lat / math.pi)).astype(np.float32)
        diff = smoothstep(-terminator, terminator * 2.5, ndl) * np.clip(ndl * 0.75 + 0.35, 0, 1)
        limb = 0.55 + 0.45 * nz ** 0.6
        self.shade = (np.clip(diff * limb + ambient, 0, 1.2)).astype(np.float32)
        rim = (1 - nz) ** 2.2 * np.clip(ndl + 0.35, 0, 1.3) * atm_k
        atmc = np.array(atm[::-1], np.float32)
        self.rim = (rim[..., None] * atmc * 0.85).astype(np.float32)
        # outside halo
        L2 = np.array([L[0], L[1]], np.float32)
        L2n = L2 / (np.linalg.norm(L2) + 1e-6)
        dirdot = (nx * L2n[0] + ny * L2n[1]) / (d + 1e-6)
        hal = np.exp(-np.clip(d - 1, 0, None) / max(halo, 1e-3) * 3.2) * np.clip(dirdot * 0.8 + 0.35, 0, 1) * (d >= 0.995)
        hal *= atm_k * 0.75
        self.halo = (hal[..., None] * atmc).astype(np.float32)
        self.alpha = np.clip((1 - d) * R + 0.5, 0, 1).astype(np.float32)
        self.inside = inside
        self.pad = pad

    def layer(self, tex, lon_off=0.0, tex2=None, mix=0.0, shade_mul=None, extra=None):
        th, tw = tex.shape[:2]
        mu = ((self.u0 + lon_off) % 1.0) * tw
        mv = self.v * th
        col = cv2.remap(tex, mu, mv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP).astype(np.float32)
        if tex2 is not None and mix > 0:
            col2 = cv2.remap(tex2, mu, mv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP).astype(np.float32)
            col = col * (1 - mix) + col2 * mix
        if extra is not None:
            col = extra(col, mu / tw, mv / th)
        sh = self.shade if shade_mul is None else self.shade * shade_mul
        rgb = col * sh[..., None] + self.rim
        a = self.alpha[..., None]
        out = rgb * a + self.halo * (1 - a)
        return out, self.alpha

    def composite(self, frame, cx, cy, tex, lon_off=0.0, scale=1.0, **kw):
        rgb, a = self.layer(tex, lon_off, **kw)
        add_layer(frame, rgb, a, cx, cy, scale)
        return frame


def add_layer(frame, rgb, a, cx, cy, scale=1.0):
    """Composite (premultiplied-ish) layer centered at cx,cy with optional scale. Halo is additive."""
    if scale != 1.0:
        sz = max(4, int(rgb.shape[1] * scale))
        rgb = cv2.resize(rgb, (sz, sz), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        a = cv2.resize(a, (sz, sz), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    s = rgb.shape[0]
    x0, y0 = int(round(cx - s / 2)), int(round(cy - s / 2))
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(frame.shape[1], x0 + s), min(frame.shape[0], y0 + s)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    sub = rgb[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    aa = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0][..., None]
    region = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    region = region * (1 - aa) + sub
    frame[fy0:fy1, fx0:fx1] = np.clip(region, 0, 255).astype(np.uint8)


def glow(frame, cx, cy, radius, color, strength=1.0):
    """Additive radial glow (BGR color)."""
    r = int(radius * 3)
    x0, y0 = int(cx - r), int(cy - r)
    ys, xs = np.mgrid[0:2 * r, 0:2 * r].astype(np.float32)
    d = np.sqrt((xs - r) ** 2 + (ys - r) ** 2) / radius
    g = (np.exp(-d * d * 1.2) + 0.25 * np.exp(-d * 1.2)) * strength
    lay = g[..., None] * np.array(color, np.float32)
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(frame.shape[1], x0 + 2 * r), min(frame.shape[0], y0 + 2 * r)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    sub = lay[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    frame[fy0:fy1, fx0:fx1] = np.clip(frame[fy0:fy1, fx0:fx1].astype(np.float32) + sub, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- voxel terrain
class Terrain:
    def __init__(self, seed=1, size=1024, rw=1280, rh=720, kind="plains"):
        self.size, self.rw, self.rh = size, rw, rh
        base = fbm(size, size, 2.4, seed)
        detail = fbm(size, size, 1.7, seed + 1)
        if kind == "plains":
            h = base * 32 + detail * 4
            # slab terraces like the broken plates seen by Venera 13
            h = h + np.floor(detail * 7) * 1.2
        else:
            h = base * 90 + detail * 6
        self.h = h.astype(np.float32)
        gy, gx = np.gradient(self.h)
        n = np.dstack([-gx, -gy, np.ones_like(gx) * 1.6])
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        sun = np.array([0.4, -0.3, 0.85]); sun /= np.linalg.norm(sun)
        lam = np.clip((n * sun).sum(2), 0, 1)
        cracks = smoothstep(0.0, 0.02, np.abs(fbm(size, size, 2.0, seed + 2) - 0.5))
        tone = fbm(size, size, 1.5, seed + 3)
        col = ramp(0.5 * tone + 0.5 * base, [(0, (70, 48, 30)), (0.5, (125, 85, 48)), (1, (170, 120, 70))])
        col *= (0.35 + 0.75 * lam)[..., None] * (0.55 + 0.45 * cracks)[..., None]
        self.col = np.clip(col, 0, 255).astype(np.float32)[..., ::-1].copy()
        self.emis = np.zeros((size, size, 3), np.float32)
        z = np.geomspace(1.5, 1400, 360).astype(np.float32)
        self.z = z

    def add_volcano(self, x, y, radius=160, height=230):
        s = self.size
        ys, xs = np.mgrid[0:s, 0:s].astype(np.float32)
        dx = (xs - x + s / 2) % s - s / 2
        dy = (ys - y + s / 2) % s - s / 2
        d = np.sqrt(dx * dx + dy * dy) / radius
        cone = np.clip(1 - d, 0, 1) ** 1.6 * height
        crater = np.clip(1 - d / 0.12, 0, 1) * 40
        self.h += cone - crater
        ang = np.arctan2(dy, dx)
        flows = (np.abs(np.sin(ang * 5 + 3 * fbm(s, s, 2.0, 40)) ) < 0.18) & (d < 0.75)
        heat = np.clip(1 - d / 0.75, 0, 1)
        lava = flows * heat ** 0.7 + (d < 0.13) * 1.0
        self.emis += lava[..., None] * np.array([20, 90, 255], np.float32)
        self.col *= (1 - 0.6 * lava)[..., None]

    def render(self, camx, camy, yaw, cam_alt=10.0, pitch=0.0, fov=1.1, fog_col=(80, 150, 215), fog_dist=420.0,
               sky_top=(50, 105, 170), sky_hor=(95, 170, 230), sun=None):
        rw, rh = self.rw, self.rh
        cols = np.arange(rw, dtype=np.float32)
        ang = yaw + (cols / rw - 0.5) * fov
        ca, sa = np.cos(ang), np.sin(ang)
        z = self.z[:, None]
        corr = np.cos((cols / rw - 0.5) * fov)[None, :]
        px = (camx + ca[None, :] * z / corr).astype(np.float32)
        py = (camy + sa[None, :] * z / corr).astype(np.float32)
        hs = cv2.remap(self.h, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        ground = cv2.remap(self.h, np.float32([[camx]]), np.float32([[camy]]), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)[0, 0]
        camh = ground + cam_alt
        focal = rw / (2 * math.tan(fov / 2))
        horizon = rh * 0.5 + pitch * focal
        y = horizon + (camh - hs) / z * focal
        ymin = np.minimum.accumulate(np.clip(y, -1, rh), axis=0)
        ri = np.clip(np.ceil(ymin), 0, rh).astype(np.int64)
        D = len(self.z)
        flat = (ri * rw + np.arange(rw)[None, :]).ravel()
        counts = np.bincount(flat, minlength=(rh + 1) * rw).reshape(rh + 1, rw)
        # idx[r] = number of samples whose top row is > r  -> nearest covering sample index
        rc = np.cumsum(counts[::-1], axis=0)[::-1]
        idx = rc[1:]  # rows 0..rh-1: samples with ri > r
        idx = np.clip(idx, 0, D)
        sky = idx >= D
        idc = np.minimum(idx, D - 1)
        colc = cv2.remap(self.col, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        emc = cv2.remap(self.emis, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        cc = np.arange(rw)[None, :]
        pix = colc[idc, cc]
        em = emc[idc, cc]
        zz = self.z[idc]
        f = np.exp(-zz / fog_dist)[..., None]
        fogc = np.array(fog_col, np.float32)
        img = pix * f + fogc * (1 - f) + em * np.clip(f * 1.4, 0, 1)
        # sky
        rows = np.arange(rh, dtype=np.float32)[:, None]
        tsky = np.clip((horizon - rows) / (rh * 0.6), 0, 1)[..., None]
        skyc = np.array(sky_hor, np.float32) * (1 - tsky) + np.array(sky_top, np.float32) * tsky
        skyc = np.broadcast_to(skyc, (rh, rw, 3))
        if sun is not None:
            sx, sy, sr, sc = sun
            yy, xx = np.mgrid[0:rh, 0:rw].astype(np.float32)
            dd = np.sqrt((xx - sx * rw) ** 2 + (yy - sy * rh) ** 2) / (sr * rw)
            skyc = skyc + (np.exp(-dd * dd) * 1.0 + 0.35 * np.exp(-dd * 0.6))[..., None] * np.array(sc, np.float32)
        img = np.where(sky[..., None], skyc, img)
        img = cv2.resize(np.clip(img, 0, 255).astype(np.uint8), (W, H), interpolation=cv2.INTER_LINEAR)
        return img


# ---------------------------------------------------------------- perspective cloud sea
class CloudSea:
    def __init__(self, seed=30):
        n = fbm(1024, 1024, 2.2, seed)
        n2 = fbm(1024, 1024, 1.6, seed + 1)
        x = 0.7 * n + 0.3 * n2
        self.tex = ramp(x, [(0, (150, 120, 80)), (0.45, (215, 190, 145)), (0.7, (245, 232, 200)), (1, (255, 250, 235))])[..., ::-1].astype(np.float32).copy()
        rw, rh = 960, 540
        self.rw, self.rh = rw, rh

    def render(self, t, horizon=0.42, speed=6.0, sky_top=(150, 175, 205), sky_hor=(200, 228, 245)):
        rw, rh = self.rw, self.rh
        hy = rh * horizon
        ys = np.arange(rh, dtype=np.float32)[:, None]
        xs = np.arange(rw, dtype=np.float32)[None, :]
        below = ys > hy + 0.5
        depth = 60.0 / np.maximum(ys - hy, 0.5)
        u = (xs - rw / 2) * depth * 1.2 + 512
        v = depth * 60 + t * speed
        u = np.broadcast_to(u, (rh, rw)).astype(np.float32)
        v = np.broadcast_to(v, (rh, rw)).astype(np.float32)
        c = cv2.remap(self.tex, u % 1024, v % 1024, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        fog = np.clip(np.exp(-depth / 12.0), 0, 1)[..., None]
        hazec = np.array(sky_hor, np.float32)
        c = c * fog + hazec * (1 - fog)
        tsky = np.clip((hy - ys) / hy, 0, 1)[..., None]
        sky = np.array(sky_hor, np.float32) * (1 - tsky) + np.array(sky_top, np.float32) * tsky
        sky = np.broadcast_to(sky, (rh, rw, 3))
        img = np.where(below[..., None], c, sky)
        return cv2.resize(np.clip(img, 0, 255).astype(np.uint8), (W, H), interpolation=cv2.INTER_CUBIC)
