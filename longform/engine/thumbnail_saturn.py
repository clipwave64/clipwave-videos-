"""YouTube thumbnail 1280x720 for the Saturn long-form video."""
import sys, cv2
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gfx
from scenes_saturn import sat_tex, Ringed
from render_long import text_img, paste, F_BLACK, F_BOLD
f = gfx.space_bg(5, (0, 0))
Ringed(300, B=0.38, light=(-0.55, 0.3, 0.78)).draw(f, 1380, 560, sat_tex(), 0.4)
paste(f, text_img("SATURN", F_BLACK, 180, color=(255, 255, 255)), 470, 330)
paste(f, text_img("THE RINGED", F_BLACK, 110, color=(120, 200, 255)), 470, 520)
paste(f, text_img("PLANET", F_BLACK, 110, color=(120, 200, 255)), 470, 650)
cv2.imwrite(sys.argv[1], cv2.resize(f, (1280, 720), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
