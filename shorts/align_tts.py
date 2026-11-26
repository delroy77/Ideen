"""Word timings for generated narration: Whisper listens, timings are mapped onto the script words.
Usage: py align_tts.py <narration.json> <dir> [lang]   -> <dir>/<key>.words.json for every <key>.wav
"""
import difflib, json, os, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

src, d = sys.argv[1], sys.argv[2]
lang = sys.argv[3] if len(sys.argv) > 3 else "de"
model = WhisperModel("small", device="cpu", compute_type="int8")
norm = lambda w: re.sub(r"[^\wäöüß]", "", w.lower())

for key, text in json.load(open(src, encoding="utf-8")).items():
    wav = os.path.join(d, key + ".wav")
    if not os.path.exists(wav):
        continue
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = model.transcribe(np.frombuffer(raw, np.float32), language=lang, word_timestamps=True,
                               condition_on_previous_text=False)
    heard = [(x.start, x.end, x.word.strip()) for s in segs for x in s.words or []]
    script = text.split()
    sm = difflib.SequenceMatcher(None, [norm(w) for w in script], [norm(h[2]) for h in heard], autojunk=False)
    times = [None] * len(script)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = heard[j1 + k][:2]
        elif tag == "replace" and j2 > j1:  # spread the heard span over the script words
            s0, e0 = heard[j1][0], heard[j2 - 1][1]
            n = i2 - i1
            for k in range(n):
                times[i1 + k] = (s0 + (e0 - s0) * k / n, s0 + (e0 - s0) * (k + 1) / n)
    for i, t in enumerate(times):  # fill gaps from neighbours
        if t is None:
            prev = times[i - 1][1] if i and times[i - 1] else 0.0
            times[i] = (prev, prev + 0.25)
    words = [(round(s, 2), round(e, 2), w) for (s, e), w in zip(times, script)]
    # cut anything the model babbled after the last script word
    end = words[-1][1] + 0.35
    if sm.ratio() < 0.6:
        print(key, f"WARNING: only {sm.ratio():.0%} of the script recognised - check this block")
    elif heard and heard[-1][1] > end + 0.5:
        tmp = wav + ".tmp.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-t", f"{end:.2f}",
                        "-af", "afade=t=out:st=%.2f:d=0.15" % (end - 0.15), tmp], check=True)
        os.replace(tmp, wav)
        print(key, f"trimmed babble after {end:.1f}s")
    json.dump([{"window": [0, 0], "words": words}],
              open(os.path.join(d, key + ".words.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(key, f"{sm.ratio():.0%} match, {words[-1][1]:.1f}s")
