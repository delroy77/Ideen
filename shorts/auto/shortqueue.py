"""Short queue: each short folder NNN/ has a meta.json with a status.
  py auto/shortqueue.py status   buffer size, shorts due today (fixed publish_on date first), posted today?, made today
  py auto/shortqueue.py new <video_id> <url> <creator> <hashtag>   new NNN folder (status "draft"), prints path
  py auto/shortqueue.py set <folder> key=value ...   e.g. status=ready  youtube_id=abc  (status=posted also stamps the date)
  py auto/shortqueue.py skip <video_id>              never offer this video again
  py auto/shortqueue.py week                         posted shorts of the last 7 days not yet in a compilation
Statuses: draft -> ready -> posted (or failed).
"""
import datetime, glob, json, os, sys
from common import HERE, ROOT, load, save, shorts

today = datetime.date.today().isoformat()
cmd, *args = sys.argv[1:] or ["status"]

if cmd == "status":
    all_ = shorts()
    ready = [s for s in all_ if s.get("status") == "ready"]
    due = sorted((s for s in ready if s.get("publish_on", "") <= today), key=lambda s: s.get("publish_on", "9"))
    print(json.dumps({
        "ready": len(ready),  # buffer size
        "due": [{"folder": s["folder"], "title": s.get("yt_title")} for s in due],  # post the first one
        "posted_today": any(s.get("posted") == today for s in all_),
        "made_today": sum(s.get("created") == today for s in all_),
    }, indent=1, ensure_ascii=False))
elif cmd == "new":
    vid, url, creator, tag = args
    nums = [int(os.path.basename(p)) for p in glob.glob(os.path.join(ROOT, "[0-9][0-9][0-9]"))]
    folder = os.path.join(ROOT, f"{max(nums, default=0) + 1:03d}")
    os.makedirs(os.path.join(folder, "src"))
    save(os.path.join(folder, "meta.json"), {"status": "draft", "created": today, "source_id": vid,
                                             "source_url": url, "creator": creator, "hashtag": tag})
    print(folder)
elif cmd == "set":
    path = os.path.join(args[0], "meta.json")
    meta = load(path)
    for kv in args[1:]:
        k, v = kv.split("=", 1)
        meta[k] = v
        if kv == "status=posted":
            meta["posted"] = today
    save(path, meta)
elif cmd == "skip":
    path = os.path.join(HERE, "skipped.json")
    save(path, sorted(set(load(path, [])) | set(args)))
elif cmd == "week":
    since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    week = [s for s in shorts() if s.get("status") == "posted" and s.get("posted", "") > since
            and not s.get("compilation")]
    print(json.dumps([{"folder": s["folder"], "title": s.get("yt_title"), "creator": s.get("creator"),
                       "youtube_id": s.get("youtube_id")} for s in week], indent=1, ensure_ascii=False))
else:
    sys.exit(__doc__)
