"""ClipWave video generator.

Usage:  python3 engine/make_video.py scripts/my_video.json [output_dir]

The script JSON looks like:
{
  "slug": "venus-day",                       # file name
  "category": "SPACE FACT",                  # small label at the top
  "theme": "#6c3bff",                        # main color
  "voice": "am_michael",                     # Kokoro voice
  "scenes": [                                 # one sentence + one emoji each
    {"text": "A day on Venus is longer than its year.", "emoji": "🪐"},
    ...
  ],
  "title": "...", "caption": "...", "hashtags": ["#space", ...],
  "layout": "split",                         # optional: "split" (default) or "classic"
  "bottom": "runner",                        # optional: runner | marbles | parkour (default: picked from slug)
  "caption_font": "montserrat"               # optional: montserrat (default) or poppins
}

Split layout = fact on the top half, original code-generated "satisfying gameplay" on the
bottom half (see gameplay.py), with big word-by-word captions sitting on the seam.
"""
import json
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tts  # noqa: E402
import gameplay  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
FONT_DIR = Path(__file__).resolve().parent / "fonts"
CAPTION_FONTS = {
    "montserrat": str(FONT_DIR / "Montserrat-Black.ttf"),
    "poppins": FONT_BOLD,
}
HIGHLIGHT = (255, 214, 10)
END_CARD = 2.2  # seconds of "follow" card at the end
HANDLE = "@clip.wave64"  # your username, shown on the end card


# ---------------------------------------------------------------- helpers
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    t = min(max(t, 0), 1)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def emoji_image(ch, size):
    font = ImageFont.truetype(FONT_EMOJI, 109)
    img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((80, 80), ch, font=font, embedded_color=True, anchor="mm")
    bbox = img.getbbox() or (0, 0, 160, 160)
    img = img.crop(bbox)
    scale = size / max(img.size)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)


def blob(radius, color, alpha):
    b = radius // 2
    s = radius * 2 + b * 4
    img = Image.new("RGBA", (s, s), (*color, 0))
    ImageDraw.Draw(img).ellipse((b * 2, b * 2, s - b * 2, s - b * 2), fill=(*color, alpha))
    return img.filter(ImageFilter.GaussianBlur(b))


# ---------------------------------------------------------------- captions
def build_word_timeline(scenes, times):
    """Spread each sentence's words over its spoken time (weighted by length)."""
    words = []
    for si, (scene, (s, e)) in enumerate(zip(scenes, times)):
        ws = scene["text"].split()
        weights = [len(w.strip(",.!?")) + 2.5 for w in ws]
        tot = sum(weights)
        t = s
        for w, wt in zip(ws, weights):
            d = (e - s) * wt / tot
            words.append({"w": w, "s": t, "e": t + d, "scene": si})
            t += d
    # group into caption chunks of up to 3 words / 16 chars, never across sentences
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) == 3 or sum(len(x["w"]) for x in cur) + len(w["w"]) > 16
                    or cur[-1]["scene"] != w["scene"] or cur[-1]["w"][-1] in ",.!?"):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


# ---------------------------------------------------------------- music
def make_music(duration, sr=tts.SR, seed=0):
    """Soft original ambient pad so videos aren't silent under the voice."""
    rng = random.Random(seed)
    t = np.arange(int(duration * sr)) / sr
    roots = [[220.0, 261.63, 329.63], [196.0, 246.94, 293.66],
             [174.61, 220.0, 261.63], [196.0, 246.94, 329.63]]
    rng.shuffle(roots)
    out = np.zeros_like(t)
    bar = 4.0
    for i in range(int(duration / bar) + 1):
        chord = roots[i % len(roots)]
        s, e = int(i * bar * sr), int(min(duration, (i + 1) * bar + 1.0) * sr)
        if s >= len(t):
            break
        tt = t[s:e] - t[s]
        env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, (bar + 1.0 - tt)) / 1.2)
        for f in chord:
            out[s:e] += env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.003 * tt))
        # gentle pluck on the beat
        for b in range(4):
            ps = s + int(b * sr)
            n = min(int(0.5 * sr), len(t) - ps)
            if n <= 0:
                continue
            pt = np.arange(n) / sr
            out[ps:ps + n] += 0.6 * np.exp(-pt * 7) * np.sin(2 * np.pi * chord[b % 3] * 2 * pt)
    out /= max(1e-6, np.abs(out).max())
    fade = np.minimum(1, np.minimum(t / 1.0, (duration - t) / 1.5))
    return (out * fade).astype(np.float32)


def write_wav(path, audio, sr=tts.SR):
    a = np.clip(audio, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((a * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------- render
def render(script_path, out_dir):
    spec = json.load(open(script_path, encoding="utf-8"))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = spec["slug"]
    theme = hex_rgb(spec.get("theme", "#6c3bff"))
    scenes = spec["scenes"]
    rng = random.Random(slug)
    split = spec.get("layout", "split") == "split"
    cap_font = CAPTION_FONTS.get(spec.get("caption_font", "montserrat"), FONT_BOLD)
    if not Path(cap_font).exists():
        cap_font = FONT_BOLD
    TOP = H // 2 if split else H          # height of the "fact" area
    game = None
    if split:
        style = spec.get("bottom") or gameplay.STYLES[sum(map(ord, slug)) % len(gameplay.STYLES)]
        game = gameplay.make_game(style, slug, theme, cap_font)

    # 1) voice
    voice, times = tts.speak([s["text"] for s in scenes], voice=spec.get("voice", "am_michael"))
    duration = len(voice) / tts.SR + END_CARD
    voice = np.concatenate([voice, np.zeros(int(END_CARD * tts.SR), np.float32)])
    music = make_music(duration, seed=rng.randint(0, 999))[: len(voice)]
    mixdown = voice + 0.11 * music
    mixdown /= max(1.0, np.abs(mixdown).max() / 0.95)
    wav_path = out_dir / f"{slug}.wav"
    write_wav(wav_path, mixdown)

    # 2) visuals prep
    chunks = build_word_timeline(scenes, times)
    dark = mix(theme, (8, 6, 20), 0.72)
    darker = mix(theme, (2, 2, 8), 0.92)
    bg = Image.new("RGB", (W, H))
    grad = np.linspace(0, 1, TOP)[:, None]
    arr = (np.array(dark)[None, None, :] * (1 - grad[..., None]) + np.array(darker)[None, None, :] * grad[..., None])
    bg = Image.fromarray(np.repeat(arr, W, axis=1).astype(np.uint8))
    blobs = [
        (blob(420, mix(theme, (255, 255, 255), 0.15), 120), rng.random() * 6, 0.11),
        (blob(340, mix(theme, (255, 80, 160), 0.45), 95), rng.random() * 6, 0.08),
        (blob(300, mix(theme, (40, 200, 255), 0.45), 85), rng.random() * 6, 0.13),
    ]
    stars = [(rng.random() * W, rng.random() * TOP, rng.random() * 2.5 + 1, rng.random() * 6) for _ in range(70)]
    emojis = [emoji_image(s.get("emoji", "✨"), 300 if split else 380) for s in scenes]
    # layout positions
    if split:
        Y_BRAND, Y_LABEL, Y_EMOJI, Y_CAP, CAP_SIZE, Y_BAR = 90, 150, 520, H // 2, 100, H - 70
    else:
        Y_BRAND, Y_LABEL, Y_EMOJI, Y_CAP, CAP_SIZE, Y_BAR = 130, 190, 720, 1290, 96, H - 120
    f_cap = ImageFont.truetype(FONT_BOLD, 96)
    f_label = ImageFont.truetype(FONT_BOLD, 40)
    f_brand = ImageFont.truetype(FONT_MED, 36)
    f_end1 = ImageFont.truetype(FONT_BOLD, 92)
    f_end2 = ImageFont.truetype(FONT_MED, 52)
    end_start = duration - END_CARD

    # 3) pipe frames into ffmpeg
    mp4 = out_dir / f"{slug}.mp4"
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav_path),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
        str(mp4)], stdin=subprocess.PIPE)

    n_frames = int(duration * FPS)
    for fi in range(n_frames):
        t = fi / FPS
        frame = Image.new("RGBA", (W, H))
        frame.paste(bg, (0, 0))

        # drifting glow blobs
        for k, (img, ph, sp) in enumerate(blobs):
            x = W / 2 + math.sin(t * sp * 2 + ph) * 380 - img.width / 2
            y = TOP * (0.3 + 0.2 * k) + math.cos(t * sp * 1.6 + ph) * 260 - img.height / 2
            frame.alpha_composite(img, (int(x), int(y)))

        d = ImageDraw.Draw(frame)
        # twinkling particles
        for (sx, sy, r, ph) in stars:
            yy = (sy - t * 18 * r) % TOP
            a = int(90 + 80 * math.sin(t * 2 + ph))
            d.ellipse((sx - r, yy - r, sx + r, yy + r), fill=(255, 255, 255, a))

        # brand + category label
        if game is not None:
            frame.paste(game.frame(t), (0, TOP))
            d = ImageDraw.Draw(frame)
        d.text((W / 2, Y_BRAND), "ClipWave", font=f_brand, fill=(255, 255, 255, 170), anchor="mm")
        label = spec.get("category", "DID YOU KNOW?")
        lw = d.textlength(label, font=f_label)
        d.rounded_rectangle((W / 2 - lw / 2 - 34, Y_LABEL, W / 2 + lw / 2 + 34, Y_LABEL + 72), radius=36, fill=(*HIGHLIGHT, 255))
        d.text((W / 2, Y_LABEL + 36), label, font=f_label, fill=(20, 16, 40), anchor="mm")

        if t < end_start:
            # current scene emoji with pop-in + bob
            si = 0
            for i, (s, e) in enumerate(times):
                if t >= s - 0.1:
                    si = i
            since = t - (times[si][0] - 0.1)
            sc = 0.4 + 0.6 * ease_out_back(since / 0.45)
            em = emojis[si]
            ew, eh = max(1, int(em.width * sc)), max(1, int(em.height * sc))
            emr = em.resize((ew, eh), Image.BILINEAR)
            bob = math.sin(t * 2.2) * 18
            frame.alpha_composite(emr, (int(W / 2 - ew / 2), int(Y_EMOJI - eh / 2 + bob)))

            # caption chunk with active-word highlight
            cur = None
            for ch in chunks:
                if ch[0]["s"] - 0.05 <= t:
                    cur = ch
            if cur and t <= cur[-1]["e"] + 0.6:
                txt_words = [w["w"].upper() for w in cur]
                pop = 0.85 + 0.15 * ease_out_back((t - cur[0]["s"]) / 0.18)
                f = ImageFont.truetype(cap_font, int(CAP_SIZE * pop))
                space = d.textlength(" ", font=f)
                widths = [d.textlength(w, font=f) for w in txt_words]
                # wrap into lines if too wide
                lines, line, lw_ = [], [], 0
                for i, wdt in enumerate(widths):
                    if line and lw_ + space + wdt > W - 140:
                        lines.append(line)
                        line, lw_ = [], 0
                    lw_ += (space if line else 0) + wdt
                    line.append(i)
                lines.append(line)
                y0 = Y_CAP - (len(lines) - 1) * 60
                for li, line in enumerate(lines):
                    total = sum(widths[i] for i in line) + space * (len(line) - 1)
                    x = W / 2 - total / 2
                    y = y0 + li * 120
                    for i in line:
                        w = cur[i]
                        active = w["s"] <= t < w["e"] + 0.02
                        col = HIGHLIGHT if active else (255, 255, 255)
                        d.text((x + 6, y + 8), txt_words[i], font=f, fill=(0, 0, 0, 150), anchor="lm",
                               stroke_width=10, stroke_fill=(0, 0, 0, 150))
                        d.text((x, y), txt_words[i], font=f, fill=col, anchor="lm",
                               stroke_width=10, stroke_fill=(10, 8, 25))
                        x += widths[i] + space
        else:
            # end card
            if split:
                shade = Image.new("RGBA", (W, H), (8, 6, 20, int(170 * min(1, (t - end_start) / 0.3))))
                frame.alpha_composite(shade)
                d = ImageDraw.Draw(frame)
            k = ease_out_back((t - end_start) / 0.5)
            fa = ImageFont.truetype(FONT_BOLD, max(10, int(92 * k)))
            d.text((W / 2, 820), "Follow for more", font=fa, fill=(255, 255, 255), anchor="mm",
                   stroke_width=6, stroke_fill=(10, 8, 25))
            d.text((W / 2, 940), HANDLE, font=f_end2, fill=HIGHLIGHT, anchor="mm")
            frame.alpha_composite(emoji_image("👉", 200), (W // 2 - 100, 1060 + int(math.sin(t * 6) * 10)))

        # progress bar
        p = min(1, t / duration)
        d.rounded_rectangle((80, Y_BAR, W - 80, Y_BAR + 12), radius=6, fill=(255, 255, 255, 90))
        d.rounded_rectangle((80, Y_BAR, 80 + (W - 160) * p, Y_BAR + 12), radius=6, fill=(*HIGHLIGHT, 255))

        ff.stdin.write(frame.convert("RGB").tobytes())

    ff.stdin.close()
    ff.wait()
    wav_path.unlink()

    # 4) posting info
    info = out_dir / f"{slug}.txt"
    info.write_text(
        f"TITLE:\n{spec.get('title', '')}\n\n"
        f"CAPTION:\n{spec.get('caption', '')}\n\n"
        f"HASHTAGS:\n{' '.join(spec.get('hashtags', []))}\n\n"
        "REMEMBER: turn on the 'AI-generated content' label when you post "
        "(TikTok: More options > AI-generated content; YouTube: 'Altered or synthetic content').\n",
        encoding="utf-8")
    print(f"done: {mp4} ({duration:.1f}s)")
    return mp4


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "output")
