import html
import os
import sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "avatar.png")
OUT = os.path.join(HERE, "..", "sagar-ascii.svg")

# 1. Flood-fill background isolation to get a pristine character cutout
im_raw = Image.open(SRC).convert("RGB")
arr_raw = np.array(im_raw)
bg_color = np.median([arr_raw[0, 0], arr_raw[0, -1]], axis=0)
diff = np.linalg.norm(arr_raw.astype(float) - bg_color, axis=2)

h, w = arr_raw.shape[:2]
visited = np.zeros((h, w), dtype=bool)
from collections import deque
q = deque()

for x in range(w):
    if diff[0, x] < 25: q.append((0, x)); visited[0, x] = True
    if diff[h-1, x] < 25: q.append((h-1, x)); visited[h-1, x] = True
for y in range(h):
    if diff[y, 0] < 25: q.append((y, 0)); visited[y, 0] = True
    if diff[y, w-1] < 25: q.append((y, w-1)); visited[y, w-1] = True

while q:
    cy, cx = q.popleft()
    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
        ny, nx = cy+dy, cx+dx
        if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
            if diff[ny, nx] < 32:
                visited[ny, nx] = True
                q.append((ny, nx))

rgba = np.zeros((h, w, 4), dtype=np.uint8)
rgba[:, :, :3] = arr_raw
rgba[:, :, 3] = np.where(visited, 0, 255)
im_cutout = Image.fromarray(rgba, "RGBA")

# 2. Setup ASCII target resolution
COLS = 160
ART_W_TARGET = 800
CELL_W = ART_W_TARGET / COLS
CELL_H = CELL_W * 15 / 8
ROWS = round(COLS * 8 / 15)
RAMP = " .`:-=+*cs#%@"

im_resized = im_cutout.resize((COLS, ROWS), Image.LANCZOS)
arr = np.array(im_resized)
rgb = arr[:, :, :3]
alpha = arr[:, :, 3]
gray = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])

# Tone curve
gamma = 1.15
gray_norm = np.power(gray / 255.0, gamma)

rows_txt = []
for y in range(ROWS):
    chars = []
    for x in range(COLS):
        if alpha[y, x] < 120:
            chars.append(" ")
            continue
        lum = gray_norm[y, x]
        if lum >= 0.94:
            chars.append(" ")
            continue
        idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
        idx = max(0, min(len(RAMP) - 1, idx))
        chars.append(RAMP[idx])
    rows_txt.append("".join(chars))

# 3. Assemble SVG
PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"
CURSOR = "#2f55ff"

ROW_DUR = 5.8 / ROWS
STAGGER = ROW_DUR
art_top = TITLEBAR_H + PAD * 0.35

parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">'
)
parts.append('<defs>'
             f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
             f'</linearGradient></defs>')

parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>')
parts.append(f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
             f'fill="none" stroke="{FRAME}" stroke-width="1"/>')

parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
             f'text-anchor="middle">sagar@github: ~$ ./portrait.sh</text>')

font_size = CELL_H * 0.86
for ry, line in enumerate(rows_txt):
    y = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    safe = html.escape(line)
    text = (f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">{safe}</text>')

    parts.append(
        f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
    parts.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
    )

status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
             f'sagar@github:~$ whoami <tspan fill="{INK}">Sagar Kewat</tspan></text>')
status_chars = len("sagar@github:~$ whoami Sagar Kewat ")
parts.append(f'<rect x="{PAD + status_chars * 13 * 0.6:.1f}" y="{status_y-12:.1f}" width="8" height="14" fill="{CURSOR}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>')

parts.append("</svg>")
svg_content = "".join(parts)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg_content)
print(f"wrote {OUT} ({len(svg_content)} bytes)")
