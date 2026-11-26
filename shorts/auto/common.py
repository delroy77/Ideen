import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # shorts/
YTDLP = [sys.executable, "-m", "yt_dlp", "--no-warnings", "--js-runtimes", "node"]
COOKIES = ["--cookies-from-browser", "firefox"]  # only needed for age-restricted videos


def load(path, default=None):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def save(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def shorts():
    """All short folders with a meta.json, oldest first."""
    out = []
    for m in sorted(glob.glob(os.path.join(ROOT, "[0-9][0-9][0-9]", "meta.json"))):
        meta = load(m)
        meta["folder"] = os.path.dirname(m)
        out.append(meta)
    return out
