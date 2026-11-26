"""Generate narration with Microsoft Edge neural TTS, incl. word timings.
Usage: py tts.py <narration.json> <outdir> [voice] [rate]
narration.json: {"n1": "Text ...", "n2": "..."}  ->  <outdir>/n1.mp3 + n1.words.json
"""
import asyncio, json, os, sys
import edge_tts

async def one(key, text, outdir, voice, rate):
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words, audio = [], bytearray()
    async for c in com.stream():
        if c["type"] == "audio":
            audio += c["data"]
        elif c["type"] == "WordBoundary":
            s = c["offset"] / 1e7
            words.append((round(s, 3), round(s + c["duration"] / 1e7, 3), c["text"]))
    open(os.path.join(outdir, f"{key}.mp3"), "wb").write(audio)
    json.dump([{"window": [0, 0], "words": words}],
              open(os.path.join(outdir, f"{key}.words.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(key, f"{words[-1][1]:.1f}s" if words else "no words")

async def main():
    src, outdir = sys.argv[1], sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else "de-DE-SeraphinaMultilingualNeural"
    rate = sys.argv[4] if len(sys.argv) > 4 else "+8%"
    os.makedirs(outdir, exist_ok=True)
    for k, t in json.load(open(src, encoding="utf-8")).items():
        await one(k, t, outdir, voice, rate)

asyncio.run(main())
