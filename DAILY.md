# ClipWave daily run: instructions

Every morning: research what's getting views, make **3 new videos**, upload them to this repository, and schedule them in Metricool for **tomorrow** on TikTok, Instagram Reels and YouTube Shorts. The owner is a beginner and doesn't need to do anything.

- Repository: `clipwave64/clipwave-videos-` (public; branch `main`)
- Metricool brand id: `7523553` (label clip.wave64), timezone `Europe/Ljubljana`
- Username shown in videos: `@clip.wave64`

## Folder layout
- `longform/`: the ~10-minute 16:9 space videos for YouTube (engine, scripts, finished videos + thumbnails). See step 9.
- `engine/`: generator (make_video.py, gameplay.py = original bottom-half gameplay, tts.py, setup.sh, fonts/)
- `format-notes.md`: daily log of what video formats/styles are performing and what we applied
- `scripts/`: every script JSON ever made (reference for format; check it to avoid repeats)
- `videos/YYYY-MM-DD/`: the mp4 + txt files for the day they POST
- `history.json`: every topic already covered (never repeat one)
- `posted.json`: log of every scheduled post (date, slug, time, Metricool result)

## Steps

1. **Setup.** Clone the repo (shallow), then `bash engine/setup.sh` (builds the voice engine, about 3-5 minutes). Configure git as `Claude <noreply@anthropic.com>`.

2. **Clean up old files.** Delete any `videos/YYYY-MM-DD/` folder older than 7 days (those videos are already published; Metricool has its own copy). Keeps the repo small.

3. **Research.** Search the web for what short-form content is performing right now on YouTube Shorts, TikTok and Instagram Reels: trending topics and fact formats, events/holidays/anniversaries in the next few days, big science/space/history/animal news. Stick to niches that suit this faceless voiceover-and-emoji format: space, history, psychology, science, animals, human body, geography, tech/AI facts. Skip dance trends, sound trends, anything needing a real person, politics, tragedies, and medical/financial advice.

   **Also research the FORMAT (every day).** Look up what the top-performing faceless fact Shorts/Reels/TikToks look like right now (trend reports, creator guides, caption-style roundups, platform announcements): layout (full-screen vs split-screen with gameplay on the bottom half), background style, subtitle font/case/colors/outline, words per caption, emoji use, hook length, video length, pacing (video length is fixed at about 65 s by the owner; don't change it based on trend guides). Write a short dated entry at the top of `format-notes.md` (what you found + sources + what you'll apply today). Then apply it through the script fields below, or with a small change to the engine if something new is clearly working.
   - **Copy the style, never the content.** Never download or reuse other people's videos, gameplay recordings, TV clips, music or paid fonts. The bottom-half "gameplay" is always our own code-generated animation (`engine/gameplay.py`: runner, marbles, parkour; you may add new original styles). Fonts must be free/open-licensed and saved in `engine/fonts/`. Reposted/unoriginal footage gets reach cut on Instagram and TikTok and is not monetizable on YouTube.
   - Any engine change must be tested (render a sample, look at frames) before the real videos are made. If a change breaks, revert it and use the last working style.

4. **Pick 3 topics** from 3 different niches, none already in `history.json`. Each must be a TRUE, checkable fact: verify every claim against a reliable source (NASA, Britannica, encyclopedias, peer-reviewed or major news sources). If a fact is disputed, drop it or say "scientists think". Never invent facts, quotes or numbers.

5. **Write the scripts** in `scripts/` (filename = slug + .json), same format as the existing ones:
   - `slug`: `NN-short-name` (01-03)
   - `category`: e.g. "SPACE FACT", "HISTORY FACT", "PSYCHOLOGY FACT", "ANIMAL FACT", "SCIENCE FACT"
   - `theme`: a hex color fitting the topic (vary them)
   - `voice`: one of `am_michael`, `af_heart`, `am_adam`, `af_bella`, `bm_george` (vary them)
   - `scenes`: 12-15 sentences (about 130-150 words in total), each with one fitting emoji. Sentence 1 = the hook (the most surprising part, said directly). End with a question to get comments. Write numbers as words so the voice reads them right. Sentences under ~20 words. **Owner's rule: every finished video must be about 1 minute 5 seconds (63-67 s including the end card).** That means going deeper on the topic with more checked facts, never padding; every extra claim must be verified like the rest.
   - `title` (under 70 characters, 1 emoji), `caption` (2-3 sentences, digits OK), `hashtags` (5-6, end with #shorts)
   - Style fields (from today's format research): `layout` ("split" = fact on top + gameplay on bottom, default; or "classic" full-screen), `bottom` ("runner", "marbles" or "parkour"; give each of the 3 videos a DIFFERENT one. If the owner has uploaded their OWN screen recordings to `gameplay/`, use "clip" (random recording) or "clip:<filename>" for those videos instead), `caption_font` ("montserrat" default, or "poppins"), `character`: always "swordfish" (owner's rule: every video is presented by our animated Dr. Swordfish, engine/character.py; keep his motion slow and smooth, no fast or sudden movements)

6. **Render**: `python3 engine/make_video.py scripts/<slug>.json videos/<TOMORROW>` for each (can run in parallel). Extract 2-3 frames per video with ffmpeg and LOOK at them (check: captions readable, nothing overlapping, the bottom-half gameplay moving and not glitching, Dr. Swordfish fully visible and not covered by captions); fix and re-render anything broken. Check each video's length with ffprobe; if it is outside 63-67 s, adjust the script and re-render. Split-screen renders take about 10 minutes for 3 videos in parallel (run them in the background).

7. **Upload**: commit `videos/<TOMORROW>/`, the new scripts, `format-notes.md`, any engine changes, and updated `history.json`, then push to `main`. Confirm each file is reachable at
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

9. **Long-form space video (every 3 days).** Look in `posted.json` for the newest entry with `"type": "long-form video"`. If its post_date is 3 or more days before tomorrow (or there is none), make one today, after the 3 shorts are scheduled:
   - Topic: always SPACE (owner's rule), one planet/moon/object or space-history story not already covered by a file in `longform/scripts/`. Research and fact-check exactly like the shorts (step 4); list the sources in the description.
   - Script: `longform/scripts/<slug>.json`, same format as `mars-red-planet-secrets.json` (title, voice, speed 0.94, chapters with scenes of `visual` + `lines`, optional `callout`, description ending with the AI/visuals notice and sources, ~10 tags). About 1,400-1,700 words of narration = about 10-12 minutes. Last line asks a question and invites subscribing.
   - Visuals: every scene `visual` must exist in `longform/engine/scenes.py` (Venus) or `scenes_mars.py` (Mars + generic surface/rover/descent/transfer scenes). For a new planet, add a new `scenes_<name>.py` with an original procedural texture and scenes (copy the Mars file's pattern) and hook it into `scenes.make`. Never use downloaded footage or images.
   - Render (see `longform/README.md`): narrate -> mixaudio -> `--stills` check (LOOK at 8-10 stills: subtitles readable, no glitches) -> full render with JOBS=2 (40-60 min, run in the background) -> thumbnail (`thumbnail_mars.py` pattern). If the mp4 is over 95 MB, re-encode with ffmpeg (libx264 -crf 26 -preset slow, aac 160k) so GitHub accepts it.
   - Commit `longform/` (script, engine changes, `longform/videos/<slug>.mp4` + `<slug>-thumb.jpg`) and push.
   - Schedule on YouTube ONLY with `createScheduledPost`: 2 days after today at 17:00 Europe/Ljubljana, `providers` youtube, `text` = description, media = raw URL of the mp4, `youtubeData` {title, type: "video", privacy: "public", madeForKids: false, isAiGeneratedContent: true, category: "EDUCATION", tags}. The 2-day gap is the owner's review window: tell them in the message that it's ready to watch (GitHub link) and that they can delete it in the Metricool planner if they don't like it. Log it in `posted.json` with `"type": "long-form video"`.

10. **Tell the owner** (short and friendly, beginner level): the 3 topics, when each will post tomorrow, the long-form video if one was made today (topic, when it posts, link to watch it first), one line on any format/style change you made today, and any problems. If something failed, say exactly what they need to do.
