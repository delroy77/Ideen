"""Read the build a PoE streamer linked in the video description and write <folder>/build.json.
Usage: py auto/build_info.py <folder> [pob-url]
  folder   short folder with src/video.info.json (from prepare.py)
  pob-url  optional, e.g. a link the streamer showed on screen; otherwise links are taken from the description
Supported links: pobb.in, maxroll.gg/poe/pob, pastebin.com. Prints the overlay line for short.json "info".
Exit code 1 = no readable build (then skip the info overlay).
From the PoE 2 launch date ("launch" in watchlist.json priority_games) on, PoE 2 builds from older videos are skipped.
"""
import base64, json, os, re, sys, time, urllib.request, zlib

UA = {"User-Agent": "Mozilla/5.0"}
PATTERNS = [  # (regex on description, raw-code url)
    (r"https?://pobb\.in/([\w-]+)", "https://pobb.in/{}/raw"),
    (r"https?://maxroll\.gg/poe2?/pob/([\w-]+)", "https://maxroll.gg/poe/api/pob/{}"),
    (r"https?://pastebin\.com/(?:raw/)?(\w+)", "https://pastebin.com/raw/{}"),
]

def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode().strip()

def decode(code):
    return zlib.decompress(base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))).decode("utf-8", "replace")

def short_num(v):
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= div:
            return f"{v / div:.1f}".rstrip("0").rstrip(".") + suf
    return str(round(v))

def parse(xml):
    b = re.search(r"<Build ([^>]*)>", xml).group(1)
    attr = dict(re.findall(r'(\w+)="([^"]*)"', b))
    stats = {k: float(v) for v, k in re.findall(r'<PlayerStat value="([^"]+)" stat="(\w+)"', xml)}
    stats.update({k: float(v) for k, v in re.findall(r'<PlayerStat stat="(\w+)" value="([^"]+)"', xml)})
    groups = re.findall(r"<Skill ([^>]*)>(.*?)</Skill>", xml, re.S)
    main = int(attr.get("mainSocketGroup", 1) or 1)
    skill, supports = "", []
    if groups and main <= len(groups):
        g = groups[main - 1]
        gems = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r"<Gem ([^>]*)/?>", g[1])]
        gems = [x for x in gems if x.get("enabled", "true") == "true" and x.get("nameSpec")]
        act = [x for x in gems if not x.get("skillId", "").startswith("Support")]
        pick = int(dict(re.findall(r'(\w+)="([^"]*)"', g[0])).get("mainActiveSkill", 1) or 1)
        if act:
            skill = act[min(pick, len(act)) - 1]["nameSpec"]
        supports = [x["nameSpec"] for x in gems if x.get("skillId", "").startswith("Support")]
    dps = max(stats.get(k, 0) for k in ("FullDPS", "CombinedDPS", "TotalDPS", "TotalDotDPS"))
    return {
        "game": "poe1" if attr.get("targetVersion", "").startswith("3") else "poe2",
        "class": attr.get("className", ""),
        "ascendancy": attr.get("ascendClassName", "") if attr.get("ascendClassName") != "None" else "",
        "level": int(attr.get("level", 0) or 0),
        "skill": skill,
        "supports": supports,
        "dps": round(dps),
        "life": round(stats.get("Life", 0)),
        "energy_shield": round(stats.get("EnergyShield", 0)),
    }

def overlay(d):
    top = " · ".join(x for x in (d["ascendancy"] or d["class"], d["skill"]) if x)
    bits = []
    if d["dps"]:
        bits.append(short_num(d["dps"]) + " DPS")
    pool = max(d["life"], d["energy_shield"])
    if pool:
        bits.append(short_num(pool) + (" ES" if d["energy_shield"] > d["life"] else " LIFE"))
    return (top + (r"\N" + " · ".join(bits) if bits else "")).upper()

def poe2_launch():
    """Launch date ("launch" in the PoE 2 priority_games entry): PoE 2 builds from videos before it are outdated."""
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json"), encoding="utf-8"))
    return next((p["launch"] for p in cfg.get("priority_games", []) if "launch" in p and "PoE2" in p["aliases"]), "")

def main(folder, url=None):
    info = json.load(open(os.path.join(folder, "src", "video.info.json"), encoding="utf-8"))
    text = url or info.get("description", "")
    launch, today = poe2_launch(), time.strftime("%Y-%m-%d")
    up = info.get("upload_date", "")
    uploaded = f"{up[:4]}-{up[4:6]}-{up[6:]}" if len(up) == 8 else ""
    for rx, raw in PATTERNS:
        for m in re.finditer(rx, text):
            try:
                d = parse(decode(fetch(raw.format(m.group(1)))))
            except Exception as e:
                print("skip", m.group(0), e, file=sys.stderr)
                continue
            if d["game"] == "poe2" and launch and today >= launch and uploaded and uploaded < launch:
                print("skip", m.group(0), f"PoE 2 build from {uploaded}, before the {launch} launch", file=sys.stderr)
                continue
            d["source"] = m.group(0)
            d["overlay"] = overlay(d)
            json.dump(d, open(os.path.join(folder, "build.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print(json.dumps(d, ensure_ascii=False, indent=1))
            return 0
    print("no readable build link", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
