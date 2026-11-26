"""Transcribe windows of a video with word timestamps.
Usage: py transcribe.py <video> <out.json> start-end [start-end ...]   (seconds)
"""
import json, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

video, out, *wins = sys.argv[1:]
model = WhisperModel("small", device="cpu", compute_type="int8")
result = []
for w in wins:
    a, b = map(float, w.split("-"))
    # decode via ffmpeg (avoids PyAV version issues)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", video,
                          "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, np.float32)
    segs, _ = model.transcribe(audio, language="en", word_timestamps=True,
                               condition_on_previous_text=False)
    words = [(round(x.start + a, 2), round(x.end + a, 2), x.word.strip())
             for s in segs for x in (s.words or [])]
    result.append({"window": [a, b], "words": words})
    print(f"--- {a}-{b}")
    print(" ".join(f"[{s:.1f}]{t}" for s, e, t in words))
json.dump(result, open(out, "w", encoding="utf-8"), indent=1)
