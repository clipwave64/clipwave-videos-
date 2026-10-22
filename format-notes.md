# Format notes

Newest first. Each daily run adds what short-form formats/styles are performing and what it applied.

## 2026-10-22: split-screen + bold captions (set up with the owner)
**Found**
- Split-screen "fact on top, satisfying gameplay on the bottom" (Subway Surfers / Minecraft-parkour style) is a widespread retention format on TikTok and Shorts; the bottom panel gives eyes something to follow so viewers stay longer. ([Wikipedia: Sludge content](https://en.wikipedia.org/wiki/Sludge_content))
- Using other people's footage is risky: Instagram cuts reach for accounts posting unoriginal content (only added narration/graphics/commentary count as edits). ([eMarketer, Apr 2026](https://www.emarketer.com/content/instagram-s-algorithm-clamps-down-on-repurposed--unoriginal-photos-posts))
- Top caption styles: bold sans-serif (Montserrat Bold/Black, Proxima Nova, Impact), ALL CAPS, 1-3 words at a time, white with thick black outline and the active word in yellow, placed in the middle/lower-middle, away from the right-side buttons. ([Blitzcut: TikTok caption styles 2026](https://blitzcutai.com/blog/best-caption-style-tiktok))

**Applied**
- New default `layout: "split"`: fact + emoji on the top half, original code-drawn gameplay on the bottom half (`runner`, `marbles`, `parkour`), captions sitting on the seam.
- Captions switched to Montserrat Black (OFL, in `engine/fonts/`) with a thicker outline and drop shadow.
- Gameplay shows a live counter (coins / balls / gems) to keep eyes on screen.
