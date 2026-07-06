#!/usr/bin/env python3
"""Assemble the self-contained PeacePans site: embed latin font subsets + images as data URIs."""
import base64, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).parent
BUILD = ROOT / "build"
FONTS = ROOT / "fonts"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def b64(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()

# ---- fonts: keep only /* latin */ blocks, download, inline ----
css = (FONTS / "fonts.css").read_text()
blocks = re.findall(r"/\* (\w[\w-]*) \*/\s*(@font-face \{[^}]+\})", css)
# group latin blocks by file URL; merge weight declarations for shared variable-font files
groups: dict[str, list[str]] = {}
for subset, block in blocks:
    if subset != "latin":
        continue
    url = re.search(r"url\((https://[^)]+)\)", block).group(1)
    groups.setdefault(url, []).append(block)

out_css = []
for url, blks in groups.items():
    fname = FONTS / (url.rsplit("/", 1)[1])
    if not fname.exists():
        subprocess.run(["curl", "-s", "-A", UA, url, "-o", str(fname)], check=True)
    weights = []
    for b in blks:
        weights += [int(w) for w in re.search(r"font-weight: ([\d ]+);", b).group(1).split()]
    block = blks[0]
    if len(blks) > 1:
        block = re.sub(r"font-weight: [\d ]+;", f"font-weight: {min(weights)} {max(weights)};", block)
    data = f"data:font/woff2;base64,{b64(fname)}"
    out_css.append(block.replace(url, data))
fonts_css = "\n".join(out_css)
print(f"fonts: {len(out_css)} latin faces, {sum(len(c) for c in out_css)//1024} KB inlined", file=sys.stderr)

# ---- images ----
tokens = {
    "FONTS_CSS": fonts_css,
    "IMG_FLATLAY": "data:image/jpeg;base64," + b64(BUILD / "flatlay.jpg"),
    "IMG_COLORS": "data:image/jpeg;base64," + b64(BUILD / "colors.jpg"),
    "IMG_LUC": "data:image/jpeg;base64," + b64(BUILD / "luc.jpg"),
    "IMG_TUNING": "data:image/jpeg;base64," + b64(BUILD / "tuning.jpg"),
    "IMG_CANPAN1": "data:image/jpeg;base64," + b64(BUILD / "canpan1.jpg"),
    "IMG_CANPAN2": "data:image/jpeg;base64," + b64(BUILD / "canpan2.jpg"),
    "IMG_HEROPAN": "data:image/jpeg;base64," + b64(BUILD / "heropan.jpg"),
    "IMG_MARK": "data:image/png;base64," + b64(BUILD / "mark.png"),
    "IMG_LOGO": "data:image/png;base64," + b64(BUILD / "logo.png"),
}

html = (ROOT / "template.html").read_text()
for k, v in tokens.items():
    if "{{" + k + "}}" not in html:
        print(f"WARN: token {k} unused", file=sys.stderr)
    html = html.replace("{{" + k + "}}", v)

leftover = re.findall(r"\{\{[A-Z_]+\}\}", html)
if leftover:
    sys.exit(f"ERROR: unreplaced tokens: {leftover}")

out = ROOT / "peacepans-site.html"
out.write_text(html)
print(f"wrote {out} ({out.stat().st_size/1024/1024:.2f} MB)")
