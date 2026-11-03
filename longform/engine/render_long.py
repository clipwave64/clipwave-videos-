"""Render a long-form 16:9 video from <work>/timeline.json + voice.wav.

usage: render_long.py <work_dir> <out.mp4> [--only i,j] [--stills t1,t2,...]
"""
import json, math, os, subprocess, sys, functools
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenes
from gfx import W, H

FPS = 30
FONTS = Path(__file__).resolve().parent / "fonts"
F_SUB = str(FONTS / "Inter-SemiBold.otf")
F_BOLD = str(FONTS / "InterDisplay-Bold.otf")
F_BLACK = str(FONTS / "InterDisplay-Black.otf")
ACCENT = (255, 176, 64)  # RGB


@functools.lru_cache(maxsize=512)
def text_img(text, font, size, color=(255, 255, 255), max_w=1500, shadow=True, box=None, pad=(26, 14)):
    """Render wrapped text to an RGBA numpy array (premultiplied later)."""
    fnt = ImageFont.truetype(font, size)
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if fnt.getlength(test) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    lh = int(size * 1.28)
    tw = int(max(fnt.getlength(l) for l in lines))
    iw, ih = tw + 2 * pad[0], lh * len(lines) + 2 * pad[1]
    im = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if box:
        d.rounded_rectangle([0, 0, iw - 1, ih - 1], radius=16, fill=box)
    for i, l in enumerate(lines):
        x = (iw - fnt.getlength(l)) / 2
        y = pad[1] + i * lh
        if shadow:
            for dx, dy in ((2, 2), (0, 2), (2, 0)):
                d.text((x + dx, y + dy), l, font=fnt, fill=(0, 0, 0, 170))
        d.text((x, y), l, font=fnt, fill=color + (255,))
    return np.array(im)


def paste(frame, rgba, x, y, alpha=1.0, anchor="center"):
    h, w = rgba.shape[:2]
    if anchor == "center":
        x, y = int(x - w / 2), int(y - h / 2)
    elif anchor == "topleft":
        x, y = int(x), int(y)
    elif anchor == "topright":
        x, y = int(x - w), int(y)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0:
        return
    sub = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = sub[..., 3:4] / 255.0 * alpha
    reg = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (reg * (1 - a) + sub[..., 2::-1] * a).astype(np.uint8)


_vig = None
_grain = None


def finish(frame, fi):
    global _vig, _grain
    if _vig is None:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xs - W / 2) / (W / 2)) ** 2 + ((ys - H / 2) / (H / 2)) ** 2)
        _vig = (1 - 0.28 * np.clip(d - 0.45, 0, 1) ** 1.5)[..., None].astype(np.float32)
        r = np.random.default_rng(1)
        _grain = [r.normal(0, 3.2, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
    g = cv2.resize(_grain[fi % 6], (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
    return np.clip(frame.astype(np.float32) * _vig + g, 0, 255).astype(np.uint8)


def thermometer(frame, p):
    x, y0, y1 = 1690, 200, 740
    temp = 15 + (467 - 15) * scenes.ease(min(1, p / 0.45))
    cv2.rectangle(frame, (x - 26, y0 - 6), (x + 26, y1 + 6), (35, 35, 40), -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y1 + 40), 52, (35, 35, 40), -1, cv2.LINE_AA)
    yy = int(y1 - (temp / 500) * (y1 - y0))
    cv2.rectangle(frame, (x - 14, yy), (x + 14, y1 + 10), (40, 60, 235), -1, cv2.LINE_AA)
    cv2.circle(frame, (x, y1 + 40), 40, (40, 60, 235), -1, cv2.LINE_AA)
    for v, lab in ((100, "Water boils · 100°C"), (327, "Lead melts · 327°C"), (467, "Venus · 467°C")):
        ty = int(y1 - v / 500 * (y1 - y0))
        cv2.line(frame, (x - 40, ty), (x - 26, ty), (240, 240, 240), 2, cv2.LINE_AA)
        paste_right(frame, text_img(lab, F_BOLD, 30), x - 48, ty)
    paste(frame, text_img(f"{int(temp)}°C", F_BLACK, 56, color=(255, 120, 60)), x, y0 - 60)


def paste_right(frame, img, x, y):
    paste(frame, img, x - img.shape[1], y - img.shape[0] // 2, anchor="topleft")


def build_segments(tl):
    segs, occ = [], {}
    chapters = tl["chapters"]
    flat = []
    for ci, ch in enumerate(chapters):
        for si, sc in enumerate(ch["scenes"]):
            t0 = ch["start"] if si == 0 else sc["start"]
            if ci == 0 and si == 0:
                t0 = 0.0
            flat.append((ci, sc, t0))
    for i, (ci, sc, t0) in enumerate(flat):
        t1 = flat[i + 1][2] if i + 1 < len(flat) else tl["duration"]
        v = sc["visual"]
        k = occ.get(v, 0); occ[v] = k + 1
        segs.append({"i": i, "ci": ci, "visual": v, "occ": k, "t0": t0, "t1": t1, "scene": sc,
                     "chapter": chapters[ci]["name"], "ch_start": chapters[ci]["start"]})
    return segs


def frame_at(seg, sc_obj, fi_global, t, total_chapters, last=False):
    t0, t1 = seg["t0"], seg["t1"]
    lt = t - t0
    p = lt / max(1e-6, t1 - t0)
    f = sc_obj.frame(lt, p).copy()
    v = seg["visual"]
    sc = seg["scene"]
    # scene-specific overlays
    if hasattr(sc_obj, "labels"):
        for txt, x, y in sc_obj.labels(lt):
            paste(f, text_img(txt, F_BOLD, 34 if v != "twins" else 44, shadow=True), x, y)
    if v == "thermo":
        thermometer(f, p)
    if v == "sunrise_west":
        paste(f, text_img("WEST", F_BLACK, 40, color=(255, 230, 190)), int(0.3 * W), 700)
        paste(f, text_img("EAST", F_BLACK, 40, color=(255, 230, 190)), int(0.82 * W), 700, alpha=0.6)
    if hasattr(sc_obj, "hud"):
        paste(f, text_img(sc_obj.hud(lt, p), F_BOLD, 40, box=(10, 10, 14, 170)), W - 70, 70, anchor="topright")
    if sc.get("timer"):
        m = sc["timer"] * scenes.ease(min(1, p / 0.8))
        paste(f, text_img(f"Survived: {int(m)} min", F_BOLD, 44, box=(10, 10, 14, 170)), W - 70, 70, anchor="topright")
    # callout (top-left)
    if sc.get("callout"):
        a = min(1, max(0, (lt - (sc["start"] - t0) - 0.4) / 0.5)) * min(1, max(0, (t1 - t - 0.2) / 0.4))
        img = text_img(sc["callout"], F_BOLD, 44, color=(255, 255, 255), box=(12, 12, 16, 185), max_w=1100)
        paste(f, img, 70, 66, alpha=a, anchor="topleft")
        cv2.rectangle(f, (70, 66), (78, 66 + img.shape[0]), (64, 176, 255), -1) if a > 0.5 else None
    # subtitles
    for ln in sc["lines"]:
        if ln["start"] - 0.05 <= t <= ln["end"] + 0.25:
            img = text_img(ln["text"], F_SUB, 40, box=(0, 0, 0, 140), max_w=1460)
            paste(f, img, W / 2, H - 70 - img.shape[0] / 2)
            break
    # chapter title card
    if seg["ci"] > 0 and seg["ch_start"] <= t < sc["start"]:
        ct = t - seg["ch_start"]
        dur = sc["start"] - seg["ch_start"]
        a = min(1, ct / 0.45) * min(1, (dur - ct) / 0.45)
        f = (f.astype(np.float32) * (1 - 0.55 * a)).astype(np.uint8)
        paste(f, text_img(f"CHAPTER {seg['ci']}", F_BOLD, 34, color=ACCENT), W / 2, H / 2 - 70, alpha=a)
        paste(f, text_img(seg["chapter"].upper(), F_BLACK, 84, max_w=1600), W / 2, H / 2 + 10, alpha=a)
    # watermark
    paste(f, text_img("@clip.wave64", F_BOLD, 26, color=(255, 255, 255)), W - 40, H - 46, alpha=0.55, anchor="topright")
    f = finish(f, fi_global)
    # dip to black at scene boundaries
    fade = min(1, lt / 0.3, (t1 - t) / 0.3)
    if seg["i"] == 0:
        fade = min(fade, lt / 1.0)
    if last:
        fade = min(fade, (t1 - t) / 1.5)
    if fade < 1:
        f = (f.astype(np.float32) * max(0, fade)).astype(np.uint8)
    return f


def render_segment(args):
    seg, out_dir, nseg = args
    out = Path(out_dir) / f"seg_{seg['i']:03d}.mp4"
    if out.exists():
        return str(out)
    tmp = Path(out_dir) / f"seg_{seg['i']:03d}.part.mp4"
    sc_obj = scenes.make(seg["visual"], seg["t1"] - seg["t0"], seg["occ"])
    f0 = int(round(seg["t0"] * FPS)); f1 = int(round(seg["t1"] * FPS))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
           "-threads", "1", str(tmp)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        fr = frame_at(seg, sc_obj, fi, fi / FPS, nseg, last=(seg["i"] == nseg - 1))
        pr.stdin.write(fr.tobytes())
    pr.stdin.close()
    if pr.wait() == 0:
        tmp.rename(out)
    return str(out)


def main():
    work = Path(sys.argv[1]); out = Path(sys.argv[2])
    tl = json.load(open(work / "timeline.json"))
    segs = build_segments(tl)
    args = sys.argv[3:]
    if args and args[0] == "--stills":
        ts = [float(x) for x in args[1].split(",")]
        sd = work / "stills"; sd.mkdir(exist_ok=True)
        for t in ts:
            seg = next(s for s in segs if s["t0"] <= t < s["t1"])
            obj = scenes.make(seg["visual"], seg["t1"] - seg["t0"], seg["occ"])
            fr = frame_at(seg, obj, int(t * FPS), t, len(segs))
            cv2.imwrite(str(sd / f"still_{t:07.2f}_{seg['visual']}.jpg"), fr, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return
    only = None
    if args and args[0] == "--only":
        only = {int(x) for x in args[1].split(",")}
    segdir = work / "segments"; segdir.mkdir(exist_ok=True)
    todo = [(s, str(segdir), len(segs)) for s in segs if only is None or s["i"] in only]
    todo.sort(key=lambda a: -(a[0]["t1"] - a[0]["t0"]))
    with Pool(int(os.environ.get("JOBS", "2"))) as pool:
        for r in pool.imap_unordered(render_segment, todo):
            print("done", r, flush=True)
    if only is not None:
        return
    lst = segdir / "list.txt"
    lst.write_text("".join(f"file 'seg_{s['i']:03d}.mp4'\n" for s in segs))
    silent = work / "video_silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)], check=True)
    audio = work / "mix.wav" if (work / "mix.wav").exists() else work / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
