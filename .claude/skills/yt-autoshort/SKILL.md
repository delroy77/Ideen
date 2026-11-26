---
name: yt-autoshort
description: Create a complete YouTube Short automatically and for free - script, AI voice, stock clips from Pixabay, word-by-word captions, quality check and upload to the user's channel via Composio. Use for "mach einen Short über X", "erstelle automatisch Shorts", "neuer Short", "Short hochladen", or any request to produce and publish a Short from a topic.
---

# yt-autoshort

Topic in, published Short out. Everything follows `style.json` (the user's fixed style template) unless
the user overrides something for this one video.

## Before the first run in a session

1. The session must run in the cloud environment **"Ideen"**: it allows the hosts this needs and holds the
   Composio project key (injected by the proxy for `backend.composio.dev`). If Composio returns 401,
   say so and stop.
2. `pip install -q edge-tts` (once per session).
3. `PIXABAY_API_KEY` must be set (environment variable of the "Ideen" environment). Without it the Short
   renders on plain gradient backgrounds - tell the user instead of silently shipping that.
4. Read `style.json` and, if it exists, `~/.claude/youtube/voice.md` or `.claude/youtube/voice.md`.

## 1. Topic

Use the user's topic. If none is given, pick one that fits `style.json` → `topics` and that stock footage
can actually show (animals, nature, space, cities, food, the human body - not specific games, brands or
people). Say which topic you picked.

## 2. Script → plan.json

Write a spoken script of roughly `target_seconds` (German Edge voices at +10% speak about 2.7 words per
second, so 35 s ≈ 95 words), split into `scenes_min`-`scenes_max` scenes. Per scene:

- `text`: 1-2 short spoken sentences in `language`, in the tone from `style.json`.
- `query`: 1-3 **English** words for Pixabay that show what the sentence says (concrete and visual:
  "octopus swimming", not "biology fact"). Vary the queries so scenes do not repeat footage.

Rules from `/yt-shorts`:
- The first sentence is the hook. It works with no context. Run it through
  `python3 ../yt-script/hookscore.py --hook "<line>"` and rewrite (max two tries) while the verdict is WEAK.
- There is a turn: a claim, then something that complicates or proves it.
- The last line sets up the first line again (loop) or teases the next Short. No trailing off.
- `hook_overlay`: 2-4 words of on-screen text for the first two seconds, different words from the
  spoken hook.
- Facts must be true. If unsure about a fact, leave it out rather than invent it.

Then the packaging (rules from `/yt-package` and `/yt-seo`): `title` (≤ 60 characters, check with
`python3 ../yt-package/title.py --title "..."`), a 1-2 sentence `description`, 3-8 `tags`, 1-3 topic
`hashtags`. `#shorts` and the footer are added automatically from `style.json`.

Write it to `/tmp/autoshort/<slug>/plan.json` (never into the repo):

```json
{
  "slug": "oktopus-herzen",
  "hook_overlay": "3 HERZEN?!",
  "scenes": [{"text": "Ein Oktopus hat drei Herzen ...", "query": "octopus"}],
  "title": "Warum ein Oktopus 3 Herzen hat",
  "description": "...",
  "tags": ["oktopus", "fakten"],
  "hashtags": ["#oktopus"]
}
```

Optional per-video overrides in the plan: `voice`, `voice_rate`.

## 3. Render

```bash
python3 .claude/skills/yt-autoshort/autoshort.py render /tmp/autoshort/<slug>/plan.json
```

Produces `short.mp4`, `captions.ass` and `render.json` (length, clips used with Pixabay credits).
If a scene shows `"fallback": "gradient"`, no fitting clip was found: change that scene's `query` and
render again (max two tries).

## 4. Check

```bash
python3 .claude/skills/yt-autoshort/autoshort.py check /tmp/autoshort/<slug>/short.mp4
```

Checks 1080×1920, H.264, 8-58 s, audio present, loudness ≈ -14 LUFS, no black gaps, file size. On FAIL:
fix the cause (too long → shorten the script; black gap → new query) and render again, max two rounds.
Still failing → stop, do not upload, report what failed.

Also look at two or three frames yourself before uploading
(`ffmpeg -ss <t> -i short.mp4 -frames:v 1 -vf scale=360:-1 frame.png`): captions readable, footage
matches the sentence, nothing embarrassing or off-topic in the clip.

## 5. Upload

If `style.json` → `upload.auto_upload` is true, upload without asking:

```bash
python3 .claude/skills/yt-autoshort/autoshort.py upload /tmp/autoshort/<slug>/short.mp4 /tmp/autoshort/<slug>/plan.json
```

If it is false, show the title, description and the video (SendUserFile) and ask: **ship it, or change it?**

The Google OAuth app is unverified, so YouTube forces API uploads to **private** until Google audits the
app - `upload.json` → `actual_privacy` shows what YouTube set. Tell the user when it is private so they
can switch it to public in YouTube Studio.

## 6. Report

Send the finished `short.mp4` to the user (SendUserFile), then a short summary: topic, title, length,
check result, the YouTube link and its actual privacy, and anything that needed a fallback.
