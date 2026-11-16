from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent
addons = root / "addons"
manifests = sorted(addons.glob("*/*.toc"))
if not manifests:
    raise SystemExit("No add-on manifests")

versions = set()
sources = {}
for toc in manifests:
    if toc.stem != toc.parent.name:
        raise SystemExit(f"Wrong manifest name: {toc}")
    sources[toc.relative_to(addons)] = toc
    for raw in toc.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## Version:"):
            versions.add(line.partition(":")[2].strip())
        elif line and not line.startswith("#"):
            path = toc.parent / line.replace("\\", "/")
            if not path.is_file() or not path.resolve().is_relative_to(toc.parent.resolve()):
                raise SystemExit(f"Missing or invalid manifest entry: {path}")
            sources[path.relative_to(addons)] = path

if len(versions) != 1:
    raise SystemExit(f"Expected one package version, got {versions}")
dist = root / "dist"
dist.mkdir(exist_ok=True)
destination = dist / f"DelroysSuite_{versions.pop()}.zip"
with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
    for relative, path in sorted(sources.items()):
        archive.write(path, relative.as_posix())
with ZipFile(destination) as archive:
    if archive.testzip() is not None:
        raise SystemExit("ZIP verification failed")
print(destination.name)
