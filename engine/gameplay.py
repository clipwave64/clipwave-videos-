"""Original, code-generated 'satisfying gameplay' for the bottom half of split-screen videos.

Everything here is drawn from scratch (no game footage), so it is 100% our own content:
no copyright claims and no 'unoriginal / reused content' penalties.

    game = make_game("runner", seed="my-slug", theme=(108, 59, 255))
    img = game.frame(t)          # PIL RGB image, GW x GH, for time t in seconds

Styles: runner (endless-runner, 3 lanes), marbles (balls escaping a spinning ring),
parkour (blocky side-scroller jumping across gaps), and "clip" = a screen recording the
owner made THEMSELVES and uploaded to gameplay/ (never downloaded footage).
"""
import colorsys
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

GW, GH = 1080, 960
STYLES = ["runner", "marbles", "parkour"]


def _hsv(h, s=0.8, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def _vgrad(top, bottom, h, w=GW):
    g = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - g) + np.array(bottom)[None, None, :] * g
    return Image.fromarray(np.repeat(arr, w, axis=1).astype(np.uint8))


def _counter(d, font, x, y, label, value, anchor="la"):
    txt = f"{label} {value}"
    d.text((x, y), txt, font=font, fill=(255, 255, 255), anchor=anchor, stroke_width=6, stroke_fill=(15, 12, 30))


def _ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ===================================================================== runner
class Runner:
    """Endless runner seen from behind: dodge crates, jump barriers, grab coins."""

    HORIZON, SPAN, F, LANE = 230, 940, 4.0, 520
    SPEED, D_PLAYER = 13.0, 4.9

    def __init__(self, seed, theme, font):
        self.rng = random.Random(seed)
        self.font = font
        hue = self.rng.random()
        self.sky = _vgrad(_hsv(hue, 0.45, 1.0), _hsv(hue + 0.08, 0.25, 1.0), self.HORIZON)
        self.track_a = _hsv(hue + 0.55, 0.25, 0.55)
        self.track_b = _hsv(hue + 0.55, 0.25, 0.47)
        self.grass_a, self.grass_b = (88, 170, 72), (74, 150, 60)
        self.city = [(self.rng.uniform(-60, GW), self.rng.uniform(30, 120), self.rng.uniform(40, 110))
                     for _ in range(26)]
        self.city_col = _hsv(hue + 0.6, 0.35, 0.75)
        # obstacle rows: every row leaves at least one lane free
        self.rows, self.coins = [], []
        z, lane = 30.0, 0
        self.plan = []  # (z_row, target_lane, jump)
        while z < 40 * self.SPEED + 200:
            if self.rng.random() < 0.25:
                self.rows.append((z, [(-1, "low"), (0, "low"), (1, "low")]))
                self.plan.append((z, lane, True))
            else:
                free = self.rng.choice([-1, 0, 1])
                blocked = [l for l in (-1, 0, 1) if l != free]
                if self.rng.random() < 0.4:
                    blocked = [self.rng.choice(blocked)]
                    if lane not in blocked:
                        free = lane
                self.rows.append((z, [(l, "tall") for l in blocked]))
                self.plan.append((z, free, False))
                for k in range(4):
                    self.coins.append((z + 3 + k * 2.2, free))
                lane = free
            z += self.rng.uniform(15, 22)

    def s(self, d):
        return self.F / (self.F + max(d, -self.F + 0.05))

    def y(self, d):
        return self.HORIZON + self.SPAN * self.s(d)

    def x(self, lane, d):
        return GW / 2 + lane * self.LANE * self.s(d)

    def player_state(self, t):
        pos = t * self.SPEED + self.D_PLAYER
        lane_from, lane, jump_y = 0, 0, 0.0
        for z, target, jump in self.plan:
            start = z - 11.0  # start moving ~0.8 s before the row
            if pos >= start:
                lane_from = lane
                lane = target
                k = _ease((pos - start) / (0.28 * self.SPEED))
                cur = lane_from + (lane - lane_from) * k
            if jump and z - 3.5 <= pos <= z + 3.5:
                p = (pos - (z - 3.5)) / 7.0
                jump_y = 4 * p * (1 - p)
        if not self.plan or pos < self.plan[0][0] - 11:
            cur = 0
        return cur, jump_y

    def frame(self, t):
        img = Image.new("RGB", (GW, GH), self.grass_a)
        img.paste(self.sky, (0, 0))
        d = ImageDraw.Draw(img)
        # skyline drifting slowly
        for (cx, h, w) in self.city:
            xx = (cx - t * 6) % (GW + 120) - 60
            d.rectangle((xx, self.HORIZON - h, xx + w, self.HORIZON), fill=self.city_col)
        travelled = t * self.SPEED
        # ground bands (grass + track) from far to near
        band = 2.0
        off = travelled % (band * 2)
        dd = 70.0 - (70.0 % (band * 2)) - off
        while dd > -2:
            d0, d1 = dd, dd + band
            k = int(round((dd + off) / band)) % 2
            y0, y1 = self.y(d1), self.y(d0)
            d.rectangle((0, y0, GW, y1 + 1), fill=self.grass_a if k else self.grass_b)
            lx0, rx0 = self.x(-1.6, d0), self.x(1.6, d0)
            lx1, rx1 = self.x(-1.6, d1), self.x(1.6, d1)
            d.polygon([(lx1, y0), (rx1, y0), (rx0, y1), (lx0, y1)], fill=self.track_a if k else self.track_b)
            dd -= band
        # rails between lanes
        for lane in (-0.5, 0.5):
            d.line([(self.x(lane, 70), self.y(70)), (self.x(lane, -1.5), self.y(-1.5))], fill=(235, 235, 245), width=6)
        for side in (-1.6, 1.6):
            d.line([(self.x(side, 70), self.y(70)), (self.x(side, -1.5), self.y(-1.5))], fill=(250, 210, 60), width=10)
        # side posts for speed
        post_gap = 9.0
        pd = post_gap - (travelled % post_gap)
        while pd < 70:
            for side in (-2.1, 2.1):
                sx, sy, sc = self.x(side, pd), self.y(pd), self.s(pd)
                d.rectangle((sx - 9 * sc, sy - 520 * sc, sx + 9 * sc, sy), fill=(70, 70, 90))
                d.ellipse((sx - 26 * sc, sy - 560 * sc, sx + 26 * sc, sy - 510 * sc), fill=(255, 240, 160))
            pd += post_gap

        lane_now, jump = self.player_state(t)
        objs = []
        for z, items in self.rows:
            rel = z - travelled
            if -2 < rel < 70:
                for lane, kind in items:
                    objs.append((rel, "obs", lane, kind))
        coins_got = 0
        for z, lane in self.coins:
            rel = z - travelled
            if rel < self.D_PLAYER:
                coins_got += 1
            elif rel < 70:
                objs.append((rel, "coin", lane, None))
        objs.sort(key=lambda o: -o[0])
        drawn_player = False
        for rel, kind, lane, sub in objs:
            if not drawn_player and rel < self.D_PLAYER:
                self._player(d, t, lane_now, jump)
                drawn_player = True
            sc = self.s(rel)
            cx, by = self.x(lane, rel), self.y(rel)
            if kind == "coin":
                r = 70 * sc
                spin = abs(math.cos(t * 6 + rel))
                yy = by - 120 * sc
                d.ellipse((cx - r * spin - 2, yy - r, cx + r * spin + 2, yy + r), fill=(255, 205, 40),
                          outline=(200, 140, 0), width=max(1, int(8 * sc)))
                continue
            w = self.LANE * 0.78 * sc
            h = (480 if sub == "tall" else 170) * sc
            top_back = self.y(rel + 1.2)
            depth_dy = by - top_back
            col = (225, 70, 70) if sub == "tall" else (245, 245, 245)
            # top face
            d.polygon([(cx - w / 2, by - h), (cx + w / 2, by - h),
                       (cx + w / 2 * 0.86, by - h - depth_dy * 0.6), (cx - w / 2 * 0.86, by - h - depth_dy * 0.6)],
                      fill=tuple(min(255, c + 30) for c in col))
            d.rectangle((cx - w / 2, by - h, cx + w / 2, by), fill=col, outline=(30, 25, 40), width=max(1, int(10 * sc)))
            if sub == "low":
                n = 5
                for i in range(n):
                    if i % 2 == 0:
                        x0 = cx - w / 2 + w * i / n
                        d.rectangle((x0, by - h, x0 + w / n, by), fill=(230, 50, 50))
            else:
                d.line((cx - w / 2, by - h, cx + w / 2, by), fill=(150, 40, 40), width=max(1, int(14 * sc)))
                d.line((cx + w / 2, by - h, cx - w / 2, by), fill=(150, 40, 40), width=max(1, int(14 * sc)))
        if not drawn_player:
            self._player(d, t, lane_now, jump)
        _counter(d, self.font, GW - 40, 150, "COINS", coins_got, anchor="ra")
        return img

    def _player(self, d, t, lane, jump):
        sc = self.s(self.D_PLAYER)
        cx, by = self.x(lane, self.D_PLAYER), self.y(self.D_PLAYER)
        bob = abs(math.sin(t * 14)) * 14
        lift = jump * 330 + bob
        # shadow
        d.ellipse((cx - 95, by - 18, cx + 95, by + 14), fill=(40, 40, 50))
        w, h = 170, 190
        top = by - h - lift
        d.rounded_rectangle((cx - w / 2, top, cx + w / 2, by - lift), radius=46, fill=(255, 140, 30),
                            outline=(40, 25, 20), width=8)
        # backpack + legs
        d.rounded_rectangle((cx - 52, top + 52, cx + 52, top + 140), radius=20, fill=(60, 110, 230), outline=(40, 25, 20), width=6)
        step = math.sin(t * 14)
        d.rectangle((cx - 50, by - lift - 8, cx - 18, by - lift + 26 + 10 * step), fill=(40, 25, 20))
        d.rectangle((cx + 18, by - lift - 8, cx + 50, by - lift + 26 - 10 * step), fill=(40, 25, 20))


# ===================================================================== marbles
class Marbles:
    """Balls bounce inside a spinning ring; each one that escapes spawns two more."""

    def __init__(self, seed, theme, font):
        self.rng = random.Random(seed)
        self.font = font
        self.cx, self.cy, self.R = GW / 2, GH * 0.47, 360
        self.gap = math.radians(38)
        self.spin = 0.9 * self.rng.choice([-1, 1])
        self.r = 20
        self.g = 1100.0
        self.balls = [self._new_ball()]
        self.escaped = 0
        self.bounces = 0
        self.t = 0.0
        self.trail = np.zeros((GH, GW, 3), np.float32)
        self.bg = np.array(_vgrad((14, 12, 30), (4, 4, 12), GH), np.float32)
        self.hue = self.rng.random()

    def _new_ball(self):
        a = self.rng.uniform(0, 2 * math.pi)
        sp = self.rng.uniform(350, 650)
        return [self.cx + self.rng.uniform(-30, 30), self.cy + self.rng.uniform(-30, 30),
                math.cos(a) * sp, math.sin(a) * sp, self.rng.random()]

    def _step(self, dt):
        rot = self.t * self.spin
        keep, spawn = [], 0
        for b in self.balls:
            b[3] += self.g * dt
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            dx, dy = b[0] - self.cx, b[1] - self.cy
            dist = math.hypot(dx, dy)
            if dist > self.R + self.r * 3:
                if b[1] > GH + 50 or b[0] < -50 or b[0] > GW + 50:
                    spawn += 1
                    continue
                keep.append(b)  # flying away
                continue
            if dist + self.r >= self.R and dist < self.R + self.r:
                ang = (math.atan2(dy, dx) - rot) % (2 * math.pi)
                if ang < self.gap:
                    keep.append(b)  # slipping through the gap
                    continue
                nx, ny = dx / dist, dy / dist
                vn = b[2] * nx + b[3] * ny
                if vn > 0:
                    b[2] -= 2 * vn * nx
                    b[3] -= 2 * vn * ny
                    sp = math.hypot(b[2], b[3])
                    boost = max(1.0, 900 / max(sp, 1)) ** 0.25
                    b[2] *= boost
                    b[3] *= boost
                    self.bounces += 1
                    b[4] += 0.07
                over = dist + self.r - self.R
                b[0] -= nx * over
                b[1] -= ny * over
            keep.append(b)
        self.balls = keep
        for _ in range(spawn):
            self.escaped += 1
            for _ in range(2):
                if len(self.balls) < 70:
                    self.balls.append(self._new_ball())
        self.t += dt

    def frame(self, t):
        while self.t < t:
            for _ in range(4):
                self._step(1 / 120)
        self.trail *= 0.82
        layer = Image.new("RGB", (GW, GH))
        d = ImageDraw.Draw(layer)
        for b in self.balls:
            c = _hsv(self.hue + b[4], 0.75, 1.0)
            d.ellipse((b[0] - self.r, b[1] - self.r, b[0] + self.r, b[1] + self.r), fill=c)
        self.trail = np.maximum(self.trail, np.asarray(layer, np.float32))
        out = Image.fromarray(np.clip(self.bg + self.trail * 0.9, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(out)
        rot = self.t * self.spin
        a0 = math.degrees(rot + self.gap)
        a1 = math.degrees(rot + 2 * math.pi)
        ring = _hsv(self.hue + self.t * 0.05, 0.6, 1.0)
        box = (self.cx - self.R - 6, self.cy - self.R - 6, self.cx + self.R + 6, self.cy + self.R + 6)
        d.arc(box, a0, a1, fill=ring, width=14)
        for b in self.balls:
            c = _hsv(self.hue + b[4], 0.75, 1.0)
            d.ellipse((b[0] - self.r, b[1] - self.r, b[0] + self.r, b[1] + self.r), fill=c, outline=(255, 255, 255), width=3)
        _counter(d, self.font, 40, 150, "BALLS", len(self.balls))
        _counter(d, self.font, GW - 40, 150, "ESCAPED", self.escaped, anchor="ra")
        return out


# ===================================================================== parkour
class Parkour:
    """Blocky side-scroller: a cube runs and jumps across floating block platforms."""

    B = 72          # block size (px)
    SPEED = 330.0   # px / s
    PX = 330        # player screen x

    def __init__(self, seed, theme, font):
        self.rng = random.Random(seed)
        self.font = font
        hue = self.rng.random()
        self.sky = _vgrad(_hsv(hue + 0.55, 0.35, 1.0), _hsv(hue + 0.5, 0.15, 1.0), GH)
        self.grass, self.dirt, self.stone = self._tile((90, 180, 70), True), self._tile((134, 96, 67)), self._tile((120, 120, 128))
        self.hills = [(self.rng.uniform(0, 2400), self.rng.uniform(140, 300)) for _ in range(10)]
        self.clouds = [(self.rng.uniform(0, 2600), self.rng.uniform(40, 260), self.rng.uniform(90, 180)) for _ in range(8)]
        # platforms: (start_col, length, height_in_blocks)
        self.segs, col, h = [], -6, 4
        total_cols = int(45 * self.SPEED / self.B) + 40
        while col < total_cols:
            ln = self.rng.randint(3, 7) if col > 0 else 14
            self.segs.append((col, ln, h))
            col += ln + self.rng.randint(1, 3)
            h = max(3, min(7, h + self.rng.choice([-2, -1, 0, 1, 1, 2])))
        # gems hover over each gap
        self.gems = []
        for a, b in zip(self.segs, self.segs[1:]):
            gx = (a[0] + a[1] + b[0]) / 2 * self.B
            self.gems.append((gx + self.B / 2, max(a[2], b[2]) + 2.6))

    def _tile(self, base, grass_top=False):
        rng = random.Random(str(base))
        t = Image.new("RGB", (self.B, self.B), base)
        d = ImageDraw.Draw(t)
        p = self.B // 8
        for i in range(8):
            for j in range(8):
                k = rng.uniform(-22, 22)
                d.rectangle((i * p, j * p, i * p + p - 1, j * p + p - 1), fill=tuple(int(min(255, max(0, c + k))) for c in base))
        if grass_top:
            dirt = Image.new("RGB", (self.B, self.B), (134, 96, 67))
            dd = ImageDraw.Draw(dirt)
            for i in range(8):
                for j in range(8):
                    k = rng.uniform(-20, 20)
                    dd.rectangle((i * p, j * p, i * p + p - 1, j * p + p - 1), fill=tuple(int(c + k) for c in (134, 96, 67)))
            for i in range(8):
                depth = rng.choice([2, 2, 3])
                for j in range(depth):
                    k = rng.uniform(-20, 20)
                    dd.rectangle((i * p, j * p, i * p + p - 1, j * p + p - 1), fill=tuple(int(c + k) for c in base))
            t = dirt
        ImageDraw.Draw(t).rectangle((0, 0, self.B - 1, self.B - 1), outline=(0, 0, 0))
        return t

    def _ground_y(self, h):
        return GH - h * self.B  # top surface y of a platform of height h

    def player(self, wx):
        """Return (y_bottom, angle) of the player at world x (player centre)."""
        segs = self.segs
        for a, b in zip(segs, segs[1:]):
            a_end = (a[0] + a[1]) * self.B
            take_off = a_end - self.B * 0.35
            land = b[0] * self.B + self.B * 0.6
            if take_off <= wx <= land:
                p = (wx - take_off) / (land - take_off)
                y0, y1 = self._ground_y(a[2]), self._ground_y(b[2])
                apex = min(y0, y1) - self.B * 1.6
                # quadratic through (0,y0) (0.5,apex-ish) (1,y1)
                yy = (1 - p) ** 2 * y0 + 2 * (1 - p) * p * (2 * apex - (y0 + y1) / 2) + p ** 2 * y1
                return yy, p * 180
            if a[0] * self.B <= wx < take_off:
                return self._ground_y(a[2]), 0
        return self._ground_y(segs[-1][2]), 0

    def frame(self, t):
        cam = t * self.SPEED - self.PX
        img = self.sky.copy()
        d = ImageDraw.Draw(img)
        for (cx, cy, w) in self.clouds:
            x = (cx - cam * 0.15) % 2600 - 300
            d.rounded_rectangle((x, cy, x + w * 1.8, cy + w * 0.45), radius=int(w * 0.2), fill=(255, 255, 255))
        for (hx, hh) in self.hills:
            x = (hx - cam * 0.35) % 2400 - 400
            d.ellipse((x, GH - 260 - hh, x + 620, GH + 400), fill=(120, 175, 120))
        # water line at the bottom
        wave = int(math.sin(t * 3) * 6)
        d.rectangle((0, GH - self.B * 1.4 + wave, GW, GH), fill=(60, 120, 220))
        for a in self.segs:
            x0 = a[0] * self.B - cam
            if x0 > GW or x0 + a[1] * self.B < 0:
                continue
            for c in range(a[1]):
                x = int(x0 + c * self.B)
                for r in range(a[2]):
                    y = int(GH - (r + 1) * self.B)
                    tile = self.grass if r == a[2] - 1 else (self.dirt if r > a[2] - 4 else self.stone)
                    img.paste(tile, (x, y))
        got = 0
        wx_player = t * self.SPEED
        for gx, gh in self.gems:
            if gx < wx_player:
                got += 1
                continue
            x, y = gx - cam, GH - gh * self.B
            if -60 < x < GW + 60:
                bob = math.sin(t * 4 + gx) * 8
                d.polygon([(x, y - 30 + bob), (x + 24, y + bob), (x, y + 30 + bob), (x - 24, y + bob)],
                          fill=(80, 230, 240), outline=(20, 90, 120))
        yb, ang = self.player(wx_player)
        size = 64
        cube = Image.new("RGBA", (size, size), (255, 200, 40, 255))
        cd = ImageDraw.Draw(cube)
        cd.rectangle((0, 0, size - 1, size - 1), outline=(40, 25, 10), width=5)
        cd.rectangle((14, 18, 26, 30), fill=(40, 25, 10))
        cd.rectangle((38, 18, 50, 30), fill=(40, 25, 10))
        cd.rectangle((16, 42, 48, 48), fill=(40, 25, 10))
        cube = cube.rotate(-ang, resample=Image.BICUBIC, expand=True)
        img.paste(cube, (int(self.PX - cube.width / 2), int(yb - size / 2 - cube.height / 2)), cube)
        _counter(d, self.font, GW - 40, 150, "GEMS", got, anchor="ra")
        return img


# ===================================================================== your own clips
CLIP_DIR = Path(__file__).resolve().parent.parent / "gameplay"
CLIP_EXT = (".mp4", ".mov", ".m4v", ".webm")


def own_clips():
    """Gameplay recordings the OWNER made themselves and uploaded to gameplay/."""
    if not CLIP_DIR.is_dir():
        return []
    return sorted(p for p in CLIP_DIR.iterdir() if p.suffix.lower() in CLIP_EXT)


class Clip:
    """Plays a random, muted, looping part of one of the owner's own screen recordings,
    cropped to fill the bottom half."""

    def __init__(self, seed, theme, font, path=None):
        rng = random.Random(seed)
        clips = own_clips()
        if path is None:
            if not clips:
                raise FileNotFoundError("no recordings in gameplay/")
            path = clips[rng.randrange(len(clips))]
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True).stdout.strip() or 0)
        start = rng.uniform(0, max(0.0, dur - 60)) if dur > 70 else 0.0
        self.proc = subprocess.Popen([
            "ffmpeg", "-v", "quiet", "-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", str(path), "-an",
            "-vf", f"fps=30,scale={GW}:{GH}:force_original_aspect_ratio=increase,crop={GW}:{GH}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.n = 0
        self.last = Image.new("RGB", (GW, GH))

    def frame(self, t):
        want = int(round(t * 30))
        while self.n <= want:
            buf = self.proc.stdout.read(GW * GH * 3)
            if len(buf) < GW * GH * 3:
                break
            self.last = Image.frombuffer("RGB", (GW, GH), buf)
            self.n += 1
        return self.last

    def __del__(self):
        try:
            self.proc.stdout.close()
            self.proc.kill()
            self.proc.wait()
        except Exception:
            pass


def make_game(style, seed, theme, font_path):
    font = ImageFont.truetype(font_path, 44)
    if style == "clip" or style.startswith("clip:"):
        path = CLIP_DIR / style[5:] if style.startswith("clip:") else None
        return Clip(seed, theme, font, path)
    cls = {"runner": Runner, "marbles": Marbles, "parkour": Parkour}[style]
    return cls(seed, theme, font)
