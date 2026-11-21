"""YouTube thumbnail 1280x720 for the Jupiter long-form video."""
import sys, cv2
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gfx
from scenes_jupiter import jup_tex, JUP_ATM, SPOT_U
from render_long import text_img, paste, F_BLACK, F_BOLD
f = gfx.space_bg(5, (0, 0))
s = gfx.Sphere(540, light=(-0.65, 0.3, 0.7), incl=0.05, atm=JUP_ATM, atm_k=0.6)
s.composite(f, 1420, 560, jup_tex(), SPOT_U + 0.1)
paste(f, text_img("JUPITER", F_BLACK, 190, color=(255, 255, 255)), 560, 300)
paste(f, text_img("KING OF", F_BLACK, 130, color=(255, 170, 80)), 560, 520)
paste(f, text_img("PLANETS", F_BLACK, 130, color=(255, 170, 80)), 560, 670)
cv2.imwrite(sys.argv[1], cv2.resize(f, (1280, 720), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
