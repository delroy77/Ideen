"""Download only the chosen windows of a video, transcribe them and grab a check frame each.
Usage: py auto/cut.py <folder> <url> start-end [start-end ...]   (seconds in the source video)
Writes src/seg_NN.mp4, seg_NN.words.json, seg_NN.jpg and a short.json skeleton
(one clip per window, start/end relative to the segment, "orig" = source time).
Add 2 s of slack on each side; trim the clips in short.json afterwards.
"""
import os, subprocess, sys
from common import COOKIES, HERE, ROOT, YTDLP, load, save

folder, url, *wins = sys.argv[1:]
src = os.path.join(folder, "src")
os.makedirs(src, exist_ok=True)
meta = load(os.path.join(folder, "meta.json"), {})
short = {"title": "", "title_seconds": 3.5, "creator": meta.get("creator", ""),
         "layout": {"facecam": [0, 0, 480, 270], "game": [480, 0, 960, 1080]},
         "sources": {}, "fixes": {}, "clips": []}
for i, w in enumerate(wins):
    a, b = map(float, w.split("-"))
    seg = os.path.join(src, f"seg_{i:02d}")
    dl = YTDLP + ["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]", "--merge-output-format", "mp4",
                  "--download-sections", f"*{a}-{b}", "--force-keyframes-at-cuts", "-o", seg + ".mp4", url]
    if subprocess.run(dl).returncode:
        subprocess.run(dl + COOKIES, check=True)  # age-restricted: Firefox must be closed
    subprocess.run([sys.executable, os.path.join(ROOT, "transcribe.py"), seg + ".mp4", seg + ".words.json",
                    f"0-{b - a}"], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str((b - a) / 2), "-i", seg + ".mp4",
                    "-frames:v", "1", seg + ".jpg"], check=True)
    key = f"s{i}"
    short["sources"][key] = {"video": f"src/seg_{i:02d}.mp4", "words": f"src/seg_{i:02d}.words.json"}
    short["clips"].append({"src": key, "start": 0.0, "end": round(b - a, 2), "orig": [a, b]})
save(os.path.join(folder, "short.json"), short)
print("wrote", os.path.join(folder, "short.json"))
