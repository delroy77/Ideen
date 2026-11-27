"""List new viral videos that have no short yet, best first.
Usage: py auto/find_videos.py   -> writes auto/candidates.json (best first) and prints a summary (~5 min)
Sources (auto/watchlist.json):
  channels         latest uploads of big English streamers
  trending_games   YouTube search "<game> streamer" (this week), only channels with >= min_followers
Score = views per hour since upload; trending games get x1.5. Skipped ids live in auto/skipped.json.
"""
import json, os, re, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from common import HERE, YTDLP, load, shorts

cfg = load(os.path.join(HERE, "watchlist.json"))
used = {s.get("source_id") for s in shorts()} | set(load(os.path.join(HERE, "skipped.json"), []))
now = time.time()
today = time.strftime("%Y-%m-%d")
# priority_games: [{"aliases": [...], "boost": 5, "from": "YYYY-MM-DD", "until": "YYYY-MM-DD",
#   optional: "searches": [extra YouTube queries], "hot_words": [...] + "hot_boost": x (e.g. patch notes),
#             "min_followers": lower bar for search hits about this game (niche streamers)}]
prios = [p for p in cfg.get("priority_games", []) if p.get("from", "") <= today <= p["until"]]
games_all = cfg.get("pinned_games", []) + cfg.get("trending_games", [])

def ids(url, n):
    out = subprocess.run(YTDLP + ["--flat-playlist", "-I", f"1:{n}", "--print", "id", url],
                         capture_output=True, text=True).stdout.split()
    return [i for i in out if i not in used]

def info(vid):
    r = subprocess.run(YTDLP + ["-j", "--skip-download", f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, encoding="utf-8")
    return json.loads(r.stdout) if r.returncode == 0 else None

jobs = {}  # video id -> watchlist channel (or None for search hits)
for ch in cfg["channels"]:
    for vid in ids(ch["url"], cfg["per_channel"]):
        jobs[vid] = ch
queries = [f"{g} streamer" for g in games_all + [p["aliases"][0] for p in prios]]
queries += [q for p in prios for q in p.get("searches", [])]
for q in dict.fromkeys(queries):
    q = urllib.parse.quote_plus(q)
    for vid in ids(f"https://www.youtube.com/results?search_query={q}&sp=EgQIAxAB", cfg["search_results"]):
        jobs.setdefault(vid, None)

with ThreadPoolExecutor(8) as ex:
    infos = dict(zip(jobs, ex.map(info, jobs)))

found = []
for vid, d in infos.items():
    if not d:
        continue
    ch = jobs[vid]
    age_h = (now - (d.get("timestamp") or now)) / 3600
    text = f"{d['title']} {' '.join(d.get('tags') or [])}".lower()
    hit = [p for p in prios if any(a.lower() in text for a in p["aliases"])]
    min_f = min([cfg["min_followers"]] + [p.get("min_followers", cfg["min_followers"]) for p in hit])
    if (d.get("live_status") in ("is_live", "is_upcoming") or age_h > cfg["max_age_days"] * 24
            or (d.get("duration") or 0) < cfg["min_minutes"] * 60
            or (ch is None and (d.get("channel_follower_count") or 0) < min_f)
            or (d.get("language") or "en")[:2] != "en"):
        continue
    game = next((g for g in games_all if g.lower() in text), None)
    score = (d.get("view_count") or 0) / max(age_h, 1) * (1.5 if game else 1)
    for p in hit:  # priority game of the period
        game, score = p["aliases"][0], score * p["boost"]
        if any(w.lower() in text for w in p.get("hot_words", [])):
            score *= p.get("hot_boost", 1)
    creator = ch["creator"] if ch else d.get("channel")
    found.append({"id": vid, "url": d["webpage_url"], "creator": creator,
                  "hashtag": ch["hashtag"] if ch else re.sub(r"\W", "", creator or ""),
                  "game": game, "title": d["title"], "minutes": round(d["duration"] / 60), "age_h": round(age_h),
                  "views": d.get("view_count"), "followers": d.get("channel_follower_count"),
                  "score": round(score), "heatmap": bool(d.get("heatmap")), "age_limit": d.get("age_limit", 0)})
found.sort(key=lambda x: -x["score"])
json.dump(found, open(os.path.join(HERE, "candidates.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
sys.stdout.reconfigure(encoding="utf-8")
for x in found[:15]:
    print(f"{x['score']:>8} {x['creator']:<16} {x['game'] or '-':<12} {x['minutes']:>3}min {x['age_h']:>3}h  {x['title'][:60]}")
print(len(found), "candidates -> auto/candidates.json")
