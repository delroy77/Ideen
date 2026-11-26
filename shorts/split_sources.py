"""Cut each clip's surroundings out of a long source into its own small file and rewrite short.json to use them.
Usage: py split_sources.py <folder>   (run before make_short.py when the source is a multi-hour stream)

make_short.py trims with ffmpeg's trim filter, which decodes the source from 0 - very slow for clips hours in.
This cuts src/seg_NN.mp4 (clip +/- 2 s, fast -ss seek), shifts word timings, cue times and clip times to match,
keeps the original range in "orig" and writes the new short.json. Expects a single source "v" with "words".
Segments that already exist are reused - delete src/seg_* after changing clip ranges.
"""
import json, os, subprocess, sys

PAD = 2.0

def main(folder):
    os.chdir(folder)
    cfg = json.load(open("short.json", encoding="utf-8"))
    src = cfg["sources"]["v"]
    words = json.load(open(src["words"], encoding="utf-8"))
    sources = {}
    for i, c in enumerate(cfg["clips"]):
        key = f"s{i}"
        a = max(0.0, c["start"] - PAD)
        out = f"src/seg_{i:02d}.mp4"
        if not os.path.exists(out):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-i", src["video"],
                            "-t", f"{c['end'] - a + PAD:.3f}", "-c:v", "libx264", "-crf", "16", "-preset", "fast",
                            "-c:a", "aac", "-b:a", "192k", out], check=True)
        ws = [[s - a, e - a, w] for win in words for s, e, w in win["words"]
              if c["start"] - 0.05 <= s < c["end"]]
        wpath = f"src/seg_{i:02d}.words.json"
        json.dump([{"window": [0, 0], "words": ws}], open(wpath, "w", encoding="utf-8"), ensure_ascii=False)
        sources[key] = {"video": out, "words": wpath}
        c["orig"] = [c["start"], c["end"]]
        if c.get("cues"):
            c["cues"] = [[round(s - a, 3), round(e - a, 3), t] for s, e, t in c["cues"]]
        c["src"], c["start"], c["end"] = key, round(c["start"] - a, 3), round(c["end"] - a, 3)
        print(key, c["orig"], "->", c["start"], c["end"])
    cfg["sources"] = sources
    json.dump(cfg, open("short.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main(sys.argv[1])
