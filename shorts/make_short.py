"""Render a 9:16 short (facecam top, gameplay bottom) with word-highlighted subtitles.
Usage: py make_short.py <folder>   (folder contains short.json; writes short.mp4 + subs.ass)
Word files come from transcribe.py.
"""
import json, os, re, subprocess, sys

W, H, CAM_H = 1080, 1920, 608
BAD = re.compile(r"\b(nigga|niggas|fuck\w*|motherfuck\w*|shit\w*|bitch\w*)\b", re.I)

def censor(t):
    return BAD.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 2) + m.group(0)[-1]
                   if len(m.group(0)) > 2 else m.group(0), t)

def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

def load_words(path, fixes):
    out = []
    for win in json.load(open(path, encoding="utf-8")):
        for s, e, w in win["words"]:
            w = fixes.get(w.strip(",.!?"), None) if w.strip(",.!?") in fixes else w
            if not w:
                continue
            if out and (w.startswith("'") or w.startswith(".")) and abs(s - out[-1][1]) < 1.0:
                out[-1] = (out[-1][0], e, out[-1][2] + w)  # "y" + "'all", "8" + ".8"
            else:
                out.append((s, e, w))
    return sorted(set(out))

def build_ass(cfg, words_by_src):
    lines, off = [], 0.0
    for c in cfg["clips"]:
        ws = [(s, e, w) for s, e, w in words_by_src[c["src"]] if s >= c["start"] - 0.05 and s < c["end"]]
        groups, cur = [], []
        for x in ws:
            if cur and (len(cur) == 3 or x[0] - cur[-1][1] > 0.6):
                groups.append(cur); cur = []
            cur.append(x)
        if cur: groups.append(cur)
        for gi, g in enumerate(groups):
            g_end = min(g[-1][1] + 0.3, c["end"],
                        groups[gi + 1][0][0] if gi + 1 < len(groups) else 1e9)
            for i, (s, e, _) in enumerate(g):
                a = s if i else g[0][0]
                b = g[i + 1][0] if i + 1 < len(g) else g_end
                txt = " ".join((r"{\c&H00E5FF&}" + censor(w).upper() + r"{\c&HFFFFFF&}") if j == i
                               else censor(w).upper() for j, (_, _, w) in enumerate(g))
                y = 1450 if c.get("layout") == "full" else CAM_H + 170  # below face / at the seam
                lines.append(f"Dialogue: 0,{ts(off + a - c['start'])},{ts(off + b - c['start'])},Sub,,0,0,0,,"
                             + r"{\pos(540,%d)}" % y + txt)
        off += c["end"] - c["start"]
    if cfg.get("title"):
        lines.append(f"Dialogue: 1,{ts(0)},{ts(cfg['title_seconds'])},Title,,0,0,0,,{cfg['title']}")
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Arial Black,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Title,Arial Black,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,18,0,8,60,60,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return head + "\n".join(lines) + "\n"

def main(folder):
    os.chdir(folder)
    cfg = json.load(open("short.json", encoding="utf-8"))
    fixes = cfg.get("fixes", {})
    words = {k: load_words(v["words"], fixes) for k, v in cfg["sources"].items()}
    open("subs.ass", "w", encoding="utf-8").write(build_ass(cfg, words))

    fx, fy, fw, fh = cfg["layout"]["facecam"]
    gx, gy, gw, gh = cfg["layout"]["game"]
    keys = list(cfg["sources"])
    args, parts = ["ffmpeg", "-y", "-v", "error"], []
    for k in keys:
        args += ["-i", cfg["sources"][k]["video"]]
    for i, c in enumerate(cfg["clips"]):
        n = keys.index(c["src"])
        if c.get("layout") == "full":  # stream shows only the camera: centred 9:16 crop
            cw = round(1080 * W / H / 2) * 2
            cx = int(c.get("center_x", 960) - cw / 2)
            parts.append(
                f"[{n}:v]trim={c['start']}:{c['end']},setpts=PTS-STARTPTS,fps=30,"
                f"crop={cw}:1080:{cx}:0,scale={W}:{H},setsar=1[s{i}];"
                f"[{n}:a]atrim={c['start']}:{c['end']},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,"
                f"afade=t=out:st={c['end'] - c['start'] - 0.04:.3f}:d=0.04[a{i}];")
            continue
        parts.append(
            f"[{n}:v]trim={c['start']}:{c['end']},setpts=PTS-STARTPTS,fps=30,split[v{i}a][v{i}b];"
            f"[v{i}a]crop={fw}:{fh}:{fx}:{fy},scale={W}:{CAM_H}[cam{i}];"
            f"[v{i}b]crop={gw}:{gh}:{gx}:{gy},scale={W}:{H - CAM_H}[game{i}];"
            f"[cam{i}][game{i}]vstack,setsar=1[s{i}];"
            f"[{n}:a]atrim={c['start']}:{c['end']},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,"
            f"afade=t=out:st={c['end'] - c['start'] - 0.04:.3f}:d=0.04[a{i}];")
    k = len(cfg["clips"])
    parts.append("".join(f"[s{i}][a{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=1[cv][ca];"
                 "[cv]ass=subs.ass[v];[ca]loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    args += ["-filter_complex", "".join(parts), "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "short.mp4"]
    subprocess.run(args, check=True)
    print("wrote", os.path.abspath("short.mp4"))

if __name__ == "__main__":
    main(sys.argv[1])
