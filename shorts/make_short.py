"""Render a 9:16 short with word-highlighted subtitles.
Usage: py make_short.py <folder>   (folder contains short.json; writes short.mp4 + subs.ass)

Clip fields:
  src, start, end        source key and range in seconds
  layout                 "stack" (default: facecam top / game bottom), "full" (centred crop), "fit" (16:9 on blurred bg)
  tts                    narration key -> uses <tts_dir>/<key>.mp3 as audio (+ its word timings); end is computed
  bed                    volume of the original audio under tts (default 0 = muted)
  cues                   [[start, end, "text"], ...] manual subtitles in source time (e.g. translations)
  creator                name shown for 5 s whenever it changes (top-level default, per clip override)
Word files come from transcribe.py / tts.py.
"""
import json, os, re, subprocess, sys

W, H, CAM_H = 1080, 1920, 608
FIT_H = round(W * 9 / 16)
MAX_CHARS = 20  # per subtitle line at size ~72
CREATOR_SECONDS = 5  # creator name tag ("creator" in short.json, per clip overridable)
SUB_Y = {"stack": CAM_H + 170, "full": 1450, "fit": (H + FIT_H) // 2 + 170}
BAD = re.compile(r"\b(nigga|niggas|fuck\w*|motherfuck\w*|shit\w*|bitch\w*)\b", re.I)

def censor(t):
    return BAD.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 2) + m.group(0)[-1]
                   if len(m.group(0)) > 2 else m.group(0), t)

def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", path], capture_output=True, text=True).stdout)

def load_words(path, fixes, shift=0.0):
    out = []
    for win in json.load(open(path, encoding="utf-8")):
        for s, e, w in win["words"]:
            key = w.strip(",.!?")
            if key in fixes:
                w = fixes[key]
            if not w:
                continue
            if out and (w.startswith("'") or w.startswith(".")) and abs(s - out[-1][1]) < 1.0:
                out[-1] = (out[-1][0], e + shift, out[-1][2] + w)  # "y" + "'all", "8" + ".8"
            else:
                out.append((s + shift, e + shift, w))
    return sorted(set(out))

def sub_lines(c, ws, off):
    y = SUB_Y[c.get("layout", "stack")]
    pos = r"{\pos(540,%d)}" % y
    lines = []
    for a, b, text in c.get("cues", []):
        rows, row = [], ""
        for w in censor(text).upper().split():  # wrap at ~MAX_CHARS per line
            if row and len(row) + 1 + len(w) > MAX_CHARS:
                rows.append(row); row = w
            else:
                row = f"{row} {w}".strip()
        rows.append(row)
        lines.append(f"Dialogue: 0,{ts(off + a - c['start'])},{ts(off + b - c['start'])},Sub,,0,0,0,,"
                     + pos + r"\N".join(rows))
    groups, cur = [], []
    for x in ws:
        chars = sum(len(w) + 1 for _, _, w in cur) + len(x[2])
        if cur and (len(cur) == 3 or chars > MAX_CHARS or x[0] - cur[-1][1] > 0.6
                    or cur[-1][2][-1:] in ".?!:,"):
            groups.append(cur); cur = []
        cur.append(x)
    if cur: groups.append(cur)
    for gi, g in enumerate(groups):
        g_end = min(g[-1][1] + 0.3, c["end"], groups[gi + 1][0][0] if gi + 1 < len(groups) else 1e9)
        for i, (s, e, _) in enumerate(g):
            a = s if i else g[0][0]
            b = g[i + 1][0] if i + 1 < len(g) else g_end
            txt = " ".join((r"{\c&H00E5FF&}" + censor(w).upper() + r"{\c&HFFFFFF&}") if j == i
                           else censor(w).upper() for j, (_, _, w) in enumerate(g))
            lines.append(f"Dialogue: 0,{ts(off + a - c['start'])},{ts(off + b - c['start'])},Sub,,0,0,0,,"
                         + pos + txt)
    return lines

def build_ass(cfg, clip_words):
    lines, off, names = [], 0.0, []
    for c, ws in zip(cfg["clips"], clip_words):
        lines += sub_lines(c, ws, off)
        who = c.get("creator", cfg.get("creator", ""))
        if who and (not names or names[-1][1] != who):
            names.append((off, who))  # name tag whenever the creator changes
        elif not who:
            names.append((off, ""))
        off += c["end"] - c["start"]
    for i, (a, who) in enumerate(names):
        if who:
            b = min(a + CREATOR_SECONDS, names[i + 1][0] if i + 1 < len(names) else off)
            lines.append(f"Dialogue: 1,{ts(a)},{ts(b)},Creator,,0,0,0,,"
                         + r"{\an5\pos(540,%d)}" % cfg.get("creator_y", 1780) + who.upper())
    if cfg.get("title"):
        y = cfg.get("title_y", 90)
        lines.append(f"Dialogue: 1,{ts(0)},{ts(cfg['title_seconds'])},Title,,0,0,0,,"
                     + r"{\an8\pos(540,%d)}" % y + cfg["title"])
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Arial Black,{cfg.get('sub_size', 78)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Title,Arial Black,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,18,0,8,60,60,90,1
Style: Creator,Arial Black,54,&H00FFFFFF,&H00FFFFFF,&H30000000,&H00000000,1,0,0,0,100,100,2,0,3,14,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return head + "\n".join(lines) + "\n"

def video_chain(c, n, i, lay):
    trim = f"[{n}:v]trim={c['start']}:{c['end']},setpts=PTS-STARTPTS,fps=30"
    layout = c.get("layout", "stack")
    if layout == "full":  # only the camera: centred 9:16 crop
        cw = round(1080 * W / H / 2) * 2
        cx = int(c.get("center_x", 960) - cw / 2)
        return f"{trim},crop={cw}:1080:{cx}:0,scale={W}:{H},setsar=1[s{i}];"
    if layout == "fit":  # whole 16:9 frame in the middle, blurred copy as background
        return (f"{trim},split[v{i}a][v{i}b];"
                f"[v{i}a]scale=-2:{H},crop={W}:{H},boxblur=25:2,eq=brightness=-0.15[bg{i}];"
                f"[v{i}b]scale={W}:{FIT_H}[fg{i}];"
                f"[bg{i}][fg{i}]overlay=0:{(H - FIT_H) // 2},setsar=1[s{i}];")
    fx, fy, fw, fh = lay["facecam"]
    gx, gy, gw, gh = lay["game"]
    return (f"{trim},split[v{i}a][v{i}b];"
            f"[v{i}a]crop={fw}:{fh}:{fx}:{fy},scale={W}:{CAM_H}[cam{i}];"
            f"[v{i}b]crop={gw}:{gh}:{gx}:{gy},scale={W}:{H - CAM_H}[game{i}];"
            f"[cam{i}][game{i}]vstack,setsar=1[s{i}];")

def main(folder):
    os.chdir(folder)
    cfg = json.load(open("short.json", encoding="utf-8"))
    fixes = cfg.get("fixes", {})
    src_words = {k: load_words(v["words"], fixes) for k, v in cfg["sources"].items() if v.get("words")}
    tts_dir = cfg.get("tts_dir", "src/tts")

    keys = list(cfg["sources"])
    inputs = [cfg["sources"][k]["video"] for k in keys]
    clip_words = []
    for c in cfg["clips"]:
        if "tts" in c:
            mp3 = next(p for p in (os.path.join(tts_dir, c["tts"] + e) for e in (".wav", ".mp3"))
                       if os.path.exists(p))
            c["end"] = round(c["start"] + duration(mp3) + c.get("pad", 0.25), 3)
            c["_ain"] = len(inputs)
            inputs.append(mp3)
            clip_words.append(load_words(os.path.join(tts_dir, c["tts"] + ".words.json"), fixes, c["start"]))
        elif c.get("cues") or c.get("no_subs"):
            clip_words.append([])
        else:
            clip_words.append([x for x in src_words.get(c["src"], [])
                               if c["start"] - 0.05 <= x[0] < c["end"]])
    open("subs.ass", "w", encoding="utf-8").write(build_ass(cfg, clip_words))

    args, parts = ["ffmpeg", "-y", "-v", "error"], []
    for p in inputs:
        args += ["-i", p]
    for i, c in enumerate(cfg["clips"]):
        n, d = keys.index(c["src"]), c["end"] - c["start"]
        parts.append(video_chain(c, n, i, cfg.get("layout", {})))
        fade = f"afade=t=in:d=0.03,afade=t=out:st={d - 0.04:.3f}:d=0.04"
        orig = f"[{n}:a]atrim={c['start']}:{c['end']},asetpts=PTS-STARTPTS"
        if "_ain" in c:
            tts = f"[{c['_ain']}:a]aresample=48000,apad=whole_dur={d:.3f},atrim=0:{d:.3f}"
            if c.get("bed", 0):
                parts.append(f"{tts}[t{i}];{orig},aresample=48000,volume={c['bed']}[b{i}];"
                             f"[t{i}][b{i}]amix=inputs=2:duration=first:normalize=0,{fade}[a{i}];")
            else:
                parts.append(f"{tts},{fade}[a{i}];")
        else:
            parts.append(f"{orig},aresample=48000,{fade}[a{i}];")
    k = len(cfg["clips"])
    parts.append("".join(f"[s{i}][a{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=1[cv][ca];"
                 "[cv]ass=subs.ass[v];[ca]loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    args += ["-filter_complex", "".join(parts), "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "short.mp4"]
    subprocess.run(args, check=True)
    print("wrote", os.path.abspath("short.mp4"), f"{sum(c['end'] - c['start'] for c in cfg['clips']):.1f}s")

if __name__ == "__main__":
    main(sys.argv[1])
