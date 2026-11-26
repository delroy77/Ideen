#!/usr/bin/env python3
"""yt-autoshort: build, check and upload a YouTube Short from a plan file.

  python3 autoshort.py render plan.json   -> <workdir>/short.mp4 + render.json
  python3 autoshort.py check  short.mp4   -> exit 0 if the Short passes every check
  python3 autoshort.py upload short.mp4 plan.json [--privacy public|private|unlisted]

Free building blocks only: Edge TTS (voice + word timings), Pixabay (stock clips,
needs PIXABAY_API_KEY), ffmpeg (cut, captions, loudness), Composio (YouTube upload,
project key injected by the network proxy for backend.composio.dev).
"""
import argparse, asyncio, hashlib, json, os, random, re, shutil, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CA = os.environ.get("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")
COMPOSIO = "https://backend.composio.dev/api/v3.1"
AUTH_CONFIG = os.environ.get("COMPOSIO_YT_AUTH_CONFIG", "ac_5tirSr_PSNwM")
COMPOSIO_USER = os.environ.get("COMPOSIO_YT_USER", "delroy")
CACHE = Path(os.environ.get("AUTOSHORT_CACHE", "/tmp/autoshort-cache"))


def load_style():
    return json.loads((HERE / "style.json").read_text(encoding="utf-8"))


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(map(str, cmd[:6]))} ...\n{r.stderr[-2000:]}")
    return r.stdout


def probe_duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).strip())


def http_json(url, data=None, method=None, headers=None):
    h = {"Content-Type": "application/json", "x-api-key": "proxy-injected", **(headers or {})}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method or ("POST" if body else "GET"), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {url.split('?')[0]}: {e.read()[:800].decode(errors='replace')}")


# ---------------------------------------------------------------- voice
async def _tts(text, voice, rate, out):
    import certifi
    certifi.where = lambda: CA  # edge-tts builds its TLS context from certifi; trust the proxy CA
    import edge_tts
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary",
                               proxy=os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"))
    words = []
    with open(out, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"start": ch["offset"] / 1e7, "end": (ch["offset"] + ch["duration"]) / 1e7, "word": ch["text"]})
    return words


def tts(text, voice, rate, out):
    return asyncio.run(_tts(text, voice, rate, out))


# ---------------------------------------------------------------- footage
def pixabay_search(query, min_dur):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": key, "q": query[:100], "per_page": 30, "safesearch": "true", "order": "popular"})
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            hits = json.loads(r.read()).get("hits", [])
    except Exception as e:  # a failed search falls back to a plain background
        print(f"  pixabay search failed for '{query}': {e}", file=sys.stderr)
        return []
    out = []
    for h in hits:
        if h.get("duration", 0) < min_dur:
            continue
        vids = h.get("videos", {})
        pick = None
        for size in ("large", "medium", "small"):
            v = vids.get(size) or {}
            if v.get("url") and min(v.get("width", 0), v.get("height", 0)) >= 540:
                pick = v
                break
        if not pick:
            continue
        portrait = pick["height"] > pick["width"]
        out.append({"id": h["id"], "url": pick["url"], "w": pick["width"], "h": pick["height"],
                    "duration": h["duration"], "user": h.get("user", ""), "page": h.get("pageURL", ""),
                    "score": (2 if portrait else 0) + min(h.get("downloads", 0), 50000) / 50000})
    return sorted(out, key=lambda c: -c["score"])


def download(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".mp4")
    if not dst.exists():
        tmp = dst.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.rename(dst)
    return dst


# ---------------------------------------------------------------- captions
def mark_sentence_ends(words, text):
    """Flag words that end a sentence or clause, by aligning TTS words with the scene text."""
    tokens = text.split()
    norm = lambda x: re.sub(r"[^\w]", "", x.lower())
    j = 0
    for w in words:
        target = norm(w["word"])
        while j < len(tokens) and norm(tokens[j]) != target:
            j += 1
        if j < len(tokens):
            w["brk"] = bool(re.search(r"[.!?:;,…]$", tokens[j]))
            j += 1
    if words:
        words[-1]["brk"] = True


def chunk_words(words, n):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or w.get("brk"):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def ass_time(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ass_escape(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def build_ass(words, style, hook_text, total):
    c, hk = style["captions"], style["hook_overlay"]
    W, H = style["width"], style["height"]
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{c['font']},{c['size']},{c['color']},{c['color']},{c['outline_color']},&H80000000,1,0,0,0,100,100,0,0,1,{c['outline']},3,5,60,60,0,1",
        f"Style: Hook,{c['font']},{hk['size']},&H00FFFFFF,&H00FFFFFF,{hk['box_color']},{hk['box_color']},1,0,0,0,100,100,0,0,3,24,0,5,80,80,0,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    n = max(1, int(c["words_per_chunk"]))
    chunks = chunk_words(words, n)
    for ci, chunk in enumerate(chunks):
        nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else total
        for wi, w in enumerate(chunk):
            start = w["start"]
            end = chunk[wi + 1]["start"] if wi + 1 < len(chunk) else min(nxt, w["end"] + 0.6)
            parts = []
            for wj, ww in enumerate(chunk):
                t = ass_escape(ww["word"].upper() if c.get("uppercase") else ww["word"])
                parts.append(f"{{\\c{c['highlight_color']}}}{t}{{\\c{c['color']}}}" if wj == wi else t)
            lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{{\\pos({W // 2},{c['position_y']})}}{' '.join(parts)}")
    if hk.get("enabled") and hook_text:
        lines.append(f"Dialogue: 2,{ass_time(0)},{ass_time(hk['seconds'])},Hook,,0,0,0,,"
                     f"{{\\pos({W // 2},{hk['position_y']})\\fad(0,250)}}{ass_escape(hook_text)}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- render
def render(plan_path):
    style = load_style()
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    work = Path(plan_path).resolve().parent
    W, H, FPS = style["width"], style["height"], style["fps"]
    voice, rate = plan.get("voice", style["voice"]), plan.get("voice_rate", style["voice_rate"])
    scenes = plan["scenes"]
    if not (style["scenes_min"] <= len(scenes) <= style["scenes_max"]):
        print(f"warning: {len(scenes)} scenes, style wants {style['scenes_min']}-{style['scenes_max']}", file=sys.stderr)

    words, t, used, credits, seg_files, audio_files = [], 0.0, set(), [], [], []
    for i, sc in enumerate(scenes):
        a = work / f"voice_{i:02d}.mp3"
        sw = tts(sc["text"], voice, rate, a)
        dur = probe_duration(a) + (0.15 if i + 1 < len(scenes) else 0.6)
        audio_files.append((a, dur))
        mark_sentence_ends(sw, sc["text"])
        words += [{**w, "start": w["start"] + t, "end": w["end"] + t} for w in sw]

        seg = work / f"seg_{i:02d}.mp4"
        clip = next((c for c in pixabay_search(sc.get("query", ""), dur) if c["id"] not in used), None)
        dark = style.get("darken_clips", 0)
        if clip:
            used.add(clip["id"])
            src = download(clip["url"])
            off = round(random.uniform(0, max(0.0, min(clip["duration"] - dur - 0.2, 4.0))), 2)
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
                  f"eq=brightness=-{dark}:saturation=1.08,setsar=1")
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(off), "-i", str(src), "-t", f"{dur:.3f}", "-an",
                 "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(seg)])
            credits.append({"scene": i, "query": sc.get("query"), "id": clip["id"], "user": clip["user"], "page": clip["page"]})
        else:
            hue = (i * 47) % 360
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                 f"gradients=s={W}x{H}:c0=0x101828:c1=0x2a1f5c:x0=0:y0=0:x1={W}:y1={H}:speed=0.02:d={dur:.3f}:r={FPS}",
                 "-vf", f"hue=h={hue},setsar=1", "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast",
                 "-pix_fmt", "yuv420p", str(seg)])
            credits.append({"scene": i, "query": sc.get("query"), "id": None, "fallback": "gradient"})
        seg_files.append(seg)
        t += dur

    total = t
    lst = work / "segments.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in seg_files))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(work / "video_raw.mp4")])

    # voice track: each scene's audio padded to its segment length, then joined
    ins, flt = [], []
    for k, (a, dur) in enumerate(audio_files):
        ins += ["-i", str(a)]
        flt.append(f"[{k}:a]aresample=48000,apad,atrim=0:{dur:.3f}[a{k}]")
    flt.append("".join(f"[a{k}]" for k in range(len(audio_files))) + f"concat=n={len(audio_files)}:v=0:a=1,"
               f"loudnorm=I={style['loudness_lufs']}:TP=-1.5:LRA=11[out]")
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(flt), "-map", "[out]",
         "-c:a", "aac", "-b:a", "192k", str(work / "voice.m4a")])

    ass = work / "captions.ass"
    ass.write_text(build_ass(words, style, plan.get("hook_overlay", ""), total), encoding="utf-8")
    out = work / "short.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(work / "video_raw.mp4"), "-i", str(work / "voice.m4a"),
         "-vf", f"ass={ass.name}", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out)], cwd=work)

    report = {"video": str(out), "seconds": round(total, 2), "scenes": len(scenes), "words": len(words), "clips": credits}
    (work / "render.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    for p in [*seg_files, *(a for a, _ in audio_files), lst, work / "video_raw.mp4", work / "voice.m4a"]:
        p.unlink(missing_ok=True)


# ---------------------------------------------------------------- check
def check(video):
    style = load_style()
    info = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)]))
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / 1e6
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", meas)
    lufs = float(m[-1]) if m else None
    black = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.7:pix_th=0.06",
                            "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    blacks = re.findall(r"black_start:([\d.]+)", black)
    checks = [
        ("format 9:16", v.get("width") == style["width"] and v.get("height") == style["height"], f"{v.get('width')}x{v.get('height')}"),
        ("codec h264", v.get("codec_name") == "h264", v.get("codec_name")),
        ("duration", 8 <= dur <= style["max_seconds"], f"{dur:.1f}s (max {style['max_seconds']})"),
        ("audio present", a is not None, a and a.get("codec_name")),
        ("loudness", lufs is not None and abs(lufs - style["loudness_lufs"]) <= 2.5, f"{lufs} LUFS"),
        ("no black gaps", not blacks, f"{len(blacks)} found"),
        ("file size", size_mb < 256, f"{size_mb:.1f} MB"),
    ]
    ok = all(c[1] for c in checks)
    for name, passed, detail in checks:
        print(f"  {'PASS' if passed else 'FAIL'}  {name:14} {detail}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------------------------------------------------------------- upload
def upload(video, plan_path, privacy=None):
    style = load_style()
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    up = style["upload"]
    data = Path(video).read_bytes()
    req = http_json(f"{COMPOSIO}/files/upload/request", {
        "toolkit_slug": "youtube", "tool_slug": "YOUTUBE_MULTIPART_UPLOAD_VIDEO", "filename": "short.mp4",
        "mimetype": "video/mp4", "md5": hashlib.md5(data).hexdigest()})
    put_headers = {"Content-Type": "video/mp4"}
    if req.get("metadata", {}).get("storage_backend") == "azure_blob_storage":
        put_headers["x-ms-blob-type"] = "BlockBlob"
    put = urllib.request.Request(req["new_presigned_url"], data=data, method="PUT", headers=put_headers)
    with urllib.request.urlopen(put, timeout=600) as r:
        if r.status >= 300:
            sys.exit(f"staging upload failed: HTTP {r.status}")

    sess = http_json(f"{COMPOSIO}/tool_router/session", {
        "user_id": COMPOSIO_USER, "toolkits": {"enable": ["youtube"]}, "auth_configs": {"youtube": AUTH_CONFIG}})
    tags = [t.lstrip("#") for t in plan.get("tags", [])]
    desc = plan.get("description", "").rstrip()
    hashtags = " ".join(dict.fromkeys(plan.get("hashtags", []) + up["hashtags"]))
    desc = f"{desc}\n\n{hashtags}\n\n{up['description_footer']}".strip()
    args = {"title": plan["title"][:100], "description": desc[:4900], "categoryId": up["category_id"],
            "privacyStatus": privacy or up["privacy"], "tags": tags[:15],
            "videoFile": {"name": "short.mp4", "mimetype": "video/mp4", "s3key": req["key"]}}
    res = http_json(f"{COMPOSIO}/tool_router/session/{sess['session_id']}/execute",
                    {"tool_slug": "YOUTUBE_MULTIPART_UPLOAD_VIDEO", "arguments": args})
    body = res.get("data", res)
    vid = body.get("id") or (body.get("response_data") or {}).get("id")
    if not vid:
        sys.exit("upload did not return a video id:\n" + json.dumps(res, ensure_ascii=False)[:1500])
    status = (body.get("status") or (body.get("response_data") or {}).get("status") or {})
    out = {"video_id": vid, "url": f"https://youtube.com/shorts/{vid}", "requested_privacy": args["privacyStatus"],
           "actual_privacy": status.get("privacyStatus")}
    (Path(plan_path).resolve().parent / "upload.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("render").add_argument("plan")
    sub.add_parser("check").add_argument("video")
    u = sub.add_parser("upload")
    u.add_argument("video")
    u.add_argument("plan")
    u.add_argument("--privacy", choices=["public", "private", "unlisted"])
    a = ap.parse_args()
    if a.cmd == "render":
        render(a.plan)
    elif a.cmd == "check":
        sys.exit(check(a.video))
    else:
        upload(a.video, a.plan, a.privacy)


if __name__ == "__main__":
    main()
