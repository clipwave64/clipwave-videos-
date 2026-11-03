"""YouTube thumbnail 1280x720 for the Venus long-form video."""
import sys, cv2, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gfx
from render_long import text_img, paste, F_BLACK, F_BOLD
f = gfx.space_bg(5, (0, 0))
s = gfx.Sphere(520, light=(-0.65, 0.3, 0.7), incl=0.28, atm_k=1.3)
s.composite(f, 1400, 560, gfx.texture("venus_clouds"), 0.3)
gfx.glow(f, 120, 80, 180, (120, 200, 255), 0.5)
paste(f, text_img("1 DAY", F_BLACK, 190, color=(255, 255, 255)), 470, 300)
paste(f, text_img("> 1 YEAR", F_BLACK, 170, color=(255, 176, 64)), 470, 520)
paste(f, text_img("on Venus", F_BOLD, 80, color=(235, 235, 235)), 470, 720)
cv2.imwrite(sys.argv[1], cv2.resize(f, (1280, 720), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
