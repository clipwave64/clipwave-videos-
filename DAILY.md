# ClipWave daily run: instructions

Every morning: research what's getting views, make **3 new videos**, upload them to this repository, and schedule them in Metricool for **tomorrow** on TikTok, Instagram Reels and YouTube Shorts. The owner is a beginner and doesn't need to do anything.

- Repository: `clipwave64/clipwave-videos-` (public; branch `main`)
- Metricool brand id: `7523553` (label clip.wave64), timezone `Europe/Ljubljana`
- Username shown in videos: `@clip.wave64`

## Folder layout
- `engine/`: generator (make_video.py, tts.py, setup.sh)
- `scripts/`: every script JSON ever made (reference for format; check it to avoid repeats)
- `videos/YYYY-MM-DD/`: the mp4 + txt files for the day they POST
- `history.json`: every topic already covered (never repeat one)
- `posted.json`: log of every scheduled post (date, slug, time, Metricool result)

## Steps

1. **Setup.** Clone the repo (shallow), then `bash engine/setup.sh` (builds the voice engine, about 3-5 minutes). Configure git as `Claude <noreply@anthropic.com>`.

2. **Clean up old files.** Delete any `videos/YYYY-MM-DD/` folder older than 7 days (those videos are already published; Metricool has its own copy). Keeps the repo small.

3. **Research.** Search the web for what short-form content is performing right now on YouTube Shorts, TikTok and Instagram Reels: trending topics and fact formats, events/holidays/anniversaries in the next few days, big science/space/history/animal news. Stick to niches that suit this faceless voiceover-and-emoji format: space, history, psychology, science, animals, human body, geography, tech/AI facts. Skip dance trends, sound trends, anything needing a real person, politics, tragedies, and medical/financial advice.

4. **Pick 3 topics** from 3 different niches, none already in `history.json`. Each must be a TRUE, checkable fact: verify every claim against a reliable source (NASA, Britannica, encyclopedias, peer-reviewed or major news sources). If a fact is disputed, drop it or say "scientists think". Never invent facts, quotes or numbers.

5. **Write the scripts** in `scripts/` (filename = slug + .json), same format as the existing ones:
   - `slug`: `NN-short-name` (01-03)
   - `category`: e.g. "SPACE FACT", "HISTORY FACT", "PSYCHOLOGY FACT", "ANIMAL FACT", "SCIENCE FACT"
   - `theme`: a hex color fitting the topic (vary them)
   - `voice`: one of `am_michael`, `af_heart`, `am_adam`, `af_bella`, `bm_george` (vary them)
   - `scenes`: 5-7 sentences, each with one fitting emoji. Sentence 1 = the hook (the most surprising part, said directly). End with a question to get comments. Write numbers as words so the voice reads them right. Sentences under ~20 words. Target 25-40 seconds.
   - `title` (under 70 characters, 1 emoji), `caption` (2-3 sentences, digits OK), `hashtags` (5-6, end with #shorts)

6. **Render**: `python3 engine/make_video.py scripts/<slug>.json videos/<TOMORROW>` for each (can run in parallel). Extract 2-3 frames per video with ffmpeg and LOOK at them; fix and re-render anything broken.

7. **Upload**: commit `videos/<TOMORROW>/`, the new scripts, and updated `history.json`, then push to `main`. Confirm each file is reachable at
   `https://raw.githubusercontent.com/clipwave64/clipwave-videos-/main/videos/<TOMORROW>/<slug>.mp4`
   (WebFetch or a HEAD request may not work from the sandbox; trust the push if it succeeded).

8. **Schedule in Metricool.** Call `getBestTimeToPostByNetwork` (tiktok, tomorrow) and pick the 3 best hours at least 2 hours apart (typically around 10:00, 12:00, 18:00). For each video, call `createScheduledPost` with blogId 7523553, date = tomorrow at that hour (+02:00 or +01:00 depending on daylight saving), and info:
   - `providers`: tiktok, instagram, youtube
   - `text`: caption + blank line + hashtags (from the .txt)
   - `media`: [the raw.githubusercontent.com URL]
   - `autoPublish`: true, `draft`: false
   - `publicationDate`: {dateTime, timezone: "Europe/Ljubljana"}
   - `instagramData`: {type: "REEL", showReelOnFeed: true, isAiGenerated: true}
   - `youtubeData`: {title, type: "short", privacy: "public", madeForKids: false, isAiGeneratedContent: true, category: "EDUCATION", tags: hashtags without #}
   - `tiktokData`: {title, privacyOption: "PUBLIC_TO_EVERYONE", isAigc: true}
   Log each result in `posted.json` and push it. If Metricool returns a plan-limit or account error, don't retry in a loop: report the exact error to the owner.

9. **Tell the owner** (short and friendly, beginner level): the 3 topics, when each will post tomorrow, and any problems. If something failed, say exactly what they need to do.
