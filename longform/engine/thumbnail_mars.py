"""YouTube thumbnail 1280x720 for the Mars long-form video."""
import sys, cv2
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gfx
from scenes_mars import mars_tex, MARS_ATM
from render_long import text_img, paste, F_BLACK, F_BOLD
f = gfx.space_bg(5, (0, 0))
s = gfx.Sphere(520, light=(-0.65, 0.3, 0.7), incl=0.3, atm=MARS_ATM, atm_k=0.8)
s.composite(f, 1420, 560, mars_tex("canyon"), 0.55)
paste(f, text_img("MARS", F_BLACK, 210, color=(255, 255, 255)), 520, 300)
paste(f, text_img("BIGGEST", F_BLACK, 130, color=(255, 120, 60)), 520, 520)
paste(f, text_img("SECRETS", F_BLACK, 130, color=(255, 120, 60)), 520, 670)
cv2.imwrite(sys.argv[1], cv2.resize(f, (1280, 720), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
