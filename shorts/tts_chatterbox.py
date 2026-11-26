"""Generate narration locally with Chatterbox Multilingual (run with .venv-tts python).
Usage: .venv-tts\\Scripts\\python.exe tts_chatterbox.py <narration.json> <outdir> [--ref voice.wav]
       [--exag 0.5] [--cfg 0.5] [--only n1,n2] [--lang de]
Writes <outdir>/<key>.wav. Word timings: run align_tts.py afterwards (main python).
"""
import argparse, json, os, re
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

ap = argparse.ArgumentParser()
ap.add_argument("narration"); ap.add_argument("outdir")
ap.add_argument("--ref"); ap.add_argument("--exag", type=float, default=0.5)
ap.add_argument("--cfg", type=float, default=0.5); ap.add_argument("--only")
ap.add_argument("--lang", default="de"); ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--suffix", default="")
a = ap.parse_args()

os.makedirs(a.outdir, exist_ok=True)
model = ChatterboxMultilingualTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
texts = json.load(open(a.narration, encoding="utf-8"))
keys = a.only.split(",") if a.only else list(texts)
gap = torch.zeros(1, int(model.sr * 0.18))
for k in keys:
    torch.manual_seed(a.seed)
    # chunks of whole sentences, >= 80 chars: very short inputs make the model babble at the end
    parts, cur = [], ""
    for s in [s for s in re.split(r"(?<=[.!?])\s+", texts[k].strip()) if s]:
        cur = f"{cur} {s}".strip()
        if len(cur) >= 80:
            parts.append(cur); cur = ""
    if cur:
        if parts and len(cur) < 80:
            parts[-1] += " " + cur
        else:
            parts.append(cur)
    wavs = []
    for s in parts:
        wavs += [model.generate(s, language_id=a.lang, audio_prompt_path=a.ref,
                                exaggeration=a.exag, cfg_weight=a.cfg), gap]
    out = os.path.join(a.outdir, f"{k}{a.suffix}.wav")
    ta.save(out, torch.cat(wavs[:-1], dim=1), model.sr)
    print(k, out)
