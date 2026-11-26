"""Weekly compilation: all shorts of the week as one 16:9 video.
Usage: py auto/compile_week.py <out_folder> <short_folder> [<short_folder> ...]
Each short sits in the middle on a blurred copy of itself; a "subscribe" note stays on the right.
Writes <out_folder>/compilation.mp4 and chapters.txt (paste into the description).
"""
import datetime, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from make_short import duration, ts  # noqa: E402
from common import load  # noqa: E402

out, *folders = sys.argv[1:]
os.makedirs(out, exist_ok=True)
W, H, FW = 1920, 1080, 608  # FW = width of the 9:16 short at full height
args, parts, chapters, names, off = ["ffmpeg", "-y", "-v", "error"], [], [], [], 0.0
for i, f in enumerate(folders):
    mp4 = os.path.abspath(os.path.join(f, "short.mp4"))
    args += ["-i", mp4]
    meta = load(os.path.join(f, "meta.json"), {})
    chapters.append(f"{datetime.timedelta(seconds=int(off))} {meta.get('yt_title') or os.path.basename(f)}"
                    + (f" ({meta['creator']})" if meta.get("creator") else ""))
    if meta.get("creator"):  # also on the left panel: older shorts have no burned-in name tag
        names.append(f"Dialogue: 0,{ts(off)},{ts(off + 5)},Note,,0,0,0,,{{\\an5\\pos({(W - FW) // 4},{H // 2})}}"
                     + meta["creator"].upper())
    off += duration(mp4)
    parts.append(f"[{i}:v]fps=30,scale=-2:{H},split[a{i}][b{i}];"
                 f"[a{i}]scale={W}:-2,crop={W}:{H},boxblur=30:2,eq=brightness=-0.25[bg{i}];"
                 f"[bg{i}][b{i}]overlay=(W-w)/2:0,setsar=1[v{i}];"
                 f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[s{i}];")

ass = os.path.join(out, "overlay.ass")
x = W - (W - FW) // 4  # centre of the right-hand panel
open(ass, "w", encoding="utf-8").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Note,Arial Black,58,&H00FFFFFF,&H00FFFFFF,&H000000FF,&H00000000,1,0,0,0,100,100,0,0,3,16,0,5,20,20,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{ts(0)},{ts(off)},Note,,0,0,0,,{{\\an5\\pos({x},{H // 2})}}SUBSCRIBE\\NNEW CLIP\\NEVERY DAY
""" + "\n".join(names) + "\n")
n = len(folders)
parts.append("".join(f"[v{i}][s{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[cv][a];"
             "[cv]ass=overlay.ass[v]")
os.chdir(out)
subprocess.run(args + ["-filter_complex", "".join(parts), "-map", "[v]", "-map", "[a]",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "compilation.mp4"], check=True)
open("chapters.txt", "w", encoding="utf-8").write("\n".join(chapters) + "\n")
print("wrote", os.path.abspath("compilation.mp4"), f"{off / 60:.1f} min")
