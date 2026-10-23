# Format notes

Newest first. Each daily run adds what short-form formats/styles are performing and what it applied.

## 2026-10-23: hook in the first second, payoff near the loop
**Found**
- Viral faceless Shorts put the hook in the very first second (no greeting/setup); curiosity gaps and mid-action starts work best. Single-fact videos do well around 15-35 s; history stories can run a bit longer (30-50 s). ([EasyViral: 500 viral faceless Shorts](https://easyviral.ai/blog/we-analyzed-500-viral-faceless-shorts))
- Captions remain the main visual layer: bold, high-contrast sans-serif, mid-frame, away from the bottom title area and right-side buttons. Keep any music low under the voice. (same source)
- Ending the payoff right before the loop point encourages replays.

**Applied**
- No engine change (current split-screen + Montserrat captions already match).
- Each first sentence now states the surprising payoff directly; kept scripts to 6-7 short sentences; ended each on a question so the loop restarts on the hook.
- Explicit style fields in every script: split layout, runner / marbles / parkour (one each).

## 2026-10-22: split-screen + bold captions (set up with the owner)
**Found**
- Split-screen "fact on top, satisfying gameplay on the bottom" (Subway Surfers / Minecraft-parkour style) is a widespread retention format on TikTok and Shorts; the bottom panel gives eyes something to follow so viewers stay longer. ([Wikipedia: Sludge content](https://en.wikipedia.org/wiki/Sludge_content))
- Using other people's footage is risky: Instagram cuts reach for accounts posting unoriginal content (only added narration/graphics/commentary count as edits). ([eMarketer, Apr 2026](https://www.emarketer.com/content/instagram-s-algorithm-clamps-down-on-repurposed--unoriginal-photos-posts))
- Top caption styles: bold sans-serif (Montserrat Bold/Black, Proxima Nova, Impact), ALL CAPS, 1-3 words at a time, white with thick black outline and the active word in yellow, placed in the middle/lower-middle, away from the right-side buttons. ([Blitzcut: TikTok caption styles 2026](https://blitzcutai.com/blog/best-caption-style-tiktok))

**Applied**
- New default `layout: "split"`: fact + emoji on the top half, original code-drawn gameplay on the bottom half (`runner`, `marbles`, `parkour`), captions sitting on the seam.
- Captions switched to Montserrat Black (OFL, in `engine/fonts/`) with a thicker outline and drop shadow.
- Gameplay shows a live counter (coins / balls / gems) to keep eyes on screen.
