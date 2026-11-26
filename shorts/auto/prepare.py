"""Fetch info + English captions of a video (no video download) and write a readable transcript.
Usage: py auto/prepare.py <folder> <url>
Writes <folder>/src/video.info.json, captions.txt ("[h:mm:ss] text" per 30 s) and
heatmap.txt (most-watched moments, if YouTube has them).
"""
import datetime, glob, os, subprocess, sys
from common import YTDLP, load

folder, url = sys.argv[1:3]
src = os.path.join(folder, "src")
os.makedirs(src, exist_ok=True)
subprocess.run(YTDLP + ["--skip-download", "--write-info-json", "--write-auto-subs", "--write-subs",
                        "--sub-langs", "en-orig,en", "--sub-format", "json3",
                        "-o", os.path.join(src, "video.%(ext)s"), url], check=True)

def hms(t):
    return str(datetime.timedelta(seconds=int(t)))

subs = sorted(glob.glob(os.path.join(src, "video.en-orig.json3"))) or sorted(glob.glob(os.path.join(src, "video.en*.json3")))
if not subs:
    sys.exit("no English captions (maybe HTTP 429) - skip this video or retry later")
buckets = {}
for ev in load(subs[0])["events"]:
    text = "".join(s.get("utf8", "") for s in ev.get("segs", [])).replace("\n", " ").strip()
    if text:
        buckets.setdefault(ev["tStartMs"] // 30000, []).append(text)
with open(os.path.join(src, "captions.txt"), "w", encoding="utf-8") as f:
    for b in sorted(buckets):
        f.write(f"[{hms(b * 30)}] {' '.join(buckets[b])}\n")

info = load(os.path.join(src, "video.info.json"))
peaks = []
for h in sorted(info.get("heatmap") or [], key=lambda h: -h["value"]):
    if all(abs(h["start_time"] - p["start_time"]) > 60 for p in peaks):
        peaks.append(h)
    if len(peaks) == 8:
        break
with open(os.path.join(src, "heatmap.txt"), "w", encoding="utf-8") as f:
    for p in sorted(peaks, key=lambda p: p["start_time"]):
        f.write(f"{hms(p['start_time'])}-{hms(p['end_time'])}  {p['value']:.2f}\n")
print(f"{info['title']} | {hms(info['duration'])} | captions: {len(buckets)} blocks | heatmap peaks: {len(peaks)}")
