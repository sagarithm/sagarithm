#!/usr/bin/env python3
"""
Render Sagar's profile README cards as animated SVGs into cards/.
Generates dual-theme cards:
- Light theme: warm paper-and-ink aesthetic (#f3f3f1 background, #111111 ink)
- Dark theme: sleek obsidian/slate aesthetic (#0d1117 background, #f0f6fc typography, glowing accents)
- Embedded subset WOFF fonts (Instrument Serif, Geist, Geist Mono)
- Padded to tile seamlessly across rows on GitHub profile READMEs
"""
import base64
import datetime
import json
import os
import re
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "contributions.json")
OUT = os.path.join(ROOT, "cards")
FONTS = os.path.join(ROOT, "fonts")
PORTRAIT = os.path.join(ROOT, "sagar-ascii.svg")

# ---- THEME PALETTES ---------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#f3f3f1",
        "bg_deep": "#e2e2de",
        "ink": "#111111",
        "ink_soft": "#3a3a3c",
        "muted": "#6e6e73",
        "rule": "#dcdcd7",
        "frame": "#e2e2de",
        "tech": "#2f55ff",
        "oss": "#10b981",
        "agent": "#8b5cf6",
        "studio": "#ef3b2d",
        "heatmap_shades": ["#e2e2de", "#c8d3ff", "#94a8ff", "#6280ff", "#2f55ff", "#1a3be0"],
        "activity_bar_default": "#111111",
        "activity_bar_partial": "#c9c9c4",
    },
    "dark": {
        "bg": "#0d1117",
        "bg_deep": "#161b22",
        "ink": "#f0f6fc",
        "ink_soft": "#c9d1d9",
        "muted": "#8b949e",
        "rule": "#30363d",
        "frame": "#30363d",
        "tech": "#58a6ff",
        "oss": "#3fb950",
        "agent": "#bc8cff",
        "studio": "#ff7b72",
        "heatmap_shades": ["#161b22", "#0e366e", "#1158b0", "#1f6feb", "#58a6ff", "#79c0ff"],
        "activity_bar_default": "#30363d",
        "activity_bar_partial": "#21262d",
    }
}

W = 880  # standard GitHub README column width at 100%

SERIF = "'Instrument Serif', Georgia, serif"
SANS = "Geist, system-ui, -apple-system, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

FONT_FILES = {
    "serif": ("Instrument Serif", "normal", 400, "serif-400.woff"),
    "serif-i": ("Instrument Serif", "italic", 400, "serif-italic.woff"),
    "sans": ("Geist", "normal", 400, "geist-400.woff"),
    "sans-b": ("Geist", "normal", 600, "geist-600.woff"),
    "mono": ("Geist Mono", "normal", 400, "geistmono-400.woff"),
}

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}90%{transform:translateY(-1px) scale(1.01) rotate(.2deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-30px)}60%{opacity:1;transform:translateX(6px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(60px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 5s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}}
"""

def font_face(keys):
    out = []
    for k in keys:
        fam, style, weight, fn = FONT_FILES[k]
        font_path = os.path.join(FONTS, fn)
        if os.path.exists(font_path):
            b64 = base64.b64encode(open(font_path, "rb").read()).decode()
            out.append(
                f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
                f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
            )
    return "".join(out)

GAP = 12
BOTTOM = 12
COL = W / 3

def svg(w, h, body, fonts, label, extra_css="", left=0, right=0, bottom=BOTTOM):
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    w, h = w + left + right, h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if os.environ.get("STATIC"):
        css += ".r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg{display:none}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}" height="{h}" viewBox="0 0 {w:.3f} {h}" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
        f"<style>{css}</style>{body}</svg>"
    )

def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"wrote cards/{name} ({len(content) // 1024} KB)")

def d(s):
    return f'style="animation-delay:{s:.2f}s"'

def wrap(text, n):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines

def text_lines(x, y, lines, lh, attrs):
    return "".join(
        f'<text x="{x}" y="{y + i * lh}" {attrs}>{escape(l)}</text>' for i, l in enumerate(lines)
    )

# ---- 1 · Hero Card ----------------------------------------------------------
def hero(theme_name):
    t = THEMES[theme_name]
    h = 432
    portrait_svg = ""
    if os.path.exists(PORTRAIT):
        src = open(PORTRAIT, encoding="utf-8").read()
        rows = re.findall(r'<text xml:space="preserve"[^>]*\by="([\d.]+)"[^>]*>(.*?)</text>', src, re.S)
        portrait = []
        for i, (y, txt) in enumerate(rows):
            portrait.append(
                f'<text class="f" style="animation-delay:{0.20 + i * 0.015:.3f}s;animation-duration:.35s" '
                f'xml:space="preserve" x="20" y="{y}" fill="{t["ink"]}" font-size="7.2" '
                f'textLength="800" lengthAdjust="spacing">{txt}</text>'
            )
        s = 0.41
        portrait_svg = f"""
<g transform="translate(520 46) scale({s}) translate(-20 -37)" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">
  {''.join(portrait)}
</g>
"""
    border = f'<rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="14" fill="none" stroke="{t["frame"]}" stroke-width="1"/>' if theme_name == "dark" else ""
    body = f"""
<defs>
  <linearGradient id="shine_{theme_name}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">
    <stop offset="0" stop-color="{t['ink']}"/><stop offset=".42" stop-color="{t['ink']}"/>
    <stop offset=".5" stop-color="{t['tech']}"/><stop offset=".58" stop-color="{t['ink']}"/>
    <stop offset="1" stop-color="{t['ink']}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-600 0;600 0;600 0"
      keyTimes="0;.45;1" dur="7s" begin="1.6s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{h}" rx="14" fill="{t['bg']}"/>
{border}
<g class="f" {d(0)}>
  <rect class="live" x="48" y="49" width="8" height="8" rx="2" fill="{t['tech']}"/>
  <text x="66" y="57" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{t['muted']}">PRODUCT ENGINEER &#8226; FOUNDER @ PIXARTUAL</text>
</g>
<text class="r" {d(0.15)} x="44" y="185" font-family="{SERIF}" font-size="116" letter-spacing="-2.5" fill="{t['ink']}">Sagar</text>
<text class="r" {d(0.30)} x="44" y="285" font-family="{SERIF}" font-style="italic" font-size="116" letter-spacing="-2.5" fill="url(#shine_{theme_name})">Kewat</text>
<g class="r" {d(0.55)}>
  {text_lines(48, 332, ["I build AI products, autonomous agentic systems,", "and contribute to core open-source infrastructure."], 27, f'font-family="{SANS}" font-size="18" fill="{t["ink_soft"]}"')}
</g>
<g class="f" {d(0.8)}>
  <text x="48" y="396" font-family="{MONO}" font-size="13" fill="{t['ink']}">sagarithm.in</text>
  <text class="nu" x="156" y="396" font-family="{MONO}" font-size="13" fill="{t['tech']}">&#8599;</text>
</g>
{portrait_svg}
"""
    write(f"hero-{theme_name}.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
          f"Sagar Kewat. Product Engineer and AI Builder. Founder @ Pixartual. ({theme_name})"))

# ---- 2 · World Tiles --------------------------------------------------------
TILE_W, TILE_H = 880 / 3 - 8, 210

def count_up(num, word, x, y, attrs, begin, dur=1.1, frames=18):
    m = re.match(r"([\d.]+)(.*)", num)
    val, suf = (float(m.group(1)), m.group(2)) if m else (0.0, num)
    dec = len(m.group(1).split(".")[1]) if m and "." in m.group(1) else 0
    tail = f' <tspan font-style="italic">{escape(word)}</tspan>'
    if os.environ.get("STATIC"):
        return f'<text x="{x}" y="{y}" {attrs}>{escape(num)}{tail}</text>'
    out = []
    for i in range(frames + 1):
        e = 1 - (1 - i / frames) ** 3
        txt = num if i == frames else f"{val * e:.{dec}f}{suf}"
        on = begin + dur * i / frames
        off = "" if i == frames else f'<set attributeName="opacity" to="0" begin="{begin + dur * (i + 1) / frames:.3f}s"/>'
        out.append(f'<text x="{x}" y="{y}" {attrs} opacity="0">{escape(txt)}{tail}'
                   f'<set attributeName="opacity" to="1" begin="{on:.3f}s"/>{off}</text>')
    return "".join(out)

def tile(name, label, color, on, num, word, blurb, delay, pos, theme_name, font_size=36):
    lines = wrap(blurb, 34)
    blurb_svg = "".join(
        f'<text class="r" {d(delay + 0.75 + i * 0.1)} x="24" y="{150 + i * 20}" font-family="{SANS}" '
        f'font-size="14" fill="{on}" opacity=".92">{escape(l)}</text>'
        for i, l in enumerate(lines)
    )
    border = f'<rect x="0.5" y="0.5" width="{TILE_W-1}" height="{TILE_H-1}" rx="14" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>' if theme_name == "dark" else ""
    body = f"""
<defs>
  <clipPath id="card_{name}_{theme_name}"><rect width="{TILE_W}" height="{TILE_H}" rx="14"/></clipPath>
  <clipPath id="slot_{name}_{theme_name}"><rect x="0" y="62" width="{TILE_W}" height="62"/></clipPath>
  <linearGradient id="gl_{name}_{theme_name}" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
    <stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<g class="ti" {d(delay)}>
  <g clip-path="url(#card_{name}_{theme_name})">
    <rect width="{TILE_W}" height="{TILE_H}" fill="{color}"/>
    {border}
    <circle class="rg" {d(delay + 0.5)} cx="{TILE_W - 40}" cy="{TILE_H - 40}" r="60" fill="none" stroke="{on}" stroke-opacity=".5" stroke-width="2"/>
    <rect class="sh" style="animation-delay:{delay + 1.4:.2f}s" x="0" y="-20" width="90" height="{TILE_H + 40}" fill="url(#gl_{name}_{theme_name})" transform="translate(-260 0)"/>
  </g>
  <text class="sl" {d(delay + 0.35)} x="24" y="38" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{on}">{label}</text>
  <g class="ai" {d(delay + 0.5)}><text class="n" style="animation-delay:{delay + 1.3:.2f}s" x="250" y="38" font-family="{MONO}" font-size="14" fill="{on}">&#8594;</text></g>
  <g clip-path="url(#slot_{name}_{theme_name})"><g class="ro" {d(delay + 0.45)}>
    {count_up(num, word, 22, 108, f'font-family="{SERIF}" font-size="{font_size}" fill="{on}"', delay + 0.45)}
  </g></g>
  {blurb_svg}
</g>
"""
    write(f"{name}-{theme_name}.svg", svg(TILE_W, TILE_H, body, ["serif", "serif-i", "sans", "mono"],
          f"{label}: {num} {word}. {blurb}", left=4 * pos, right=8 - 4 * pos))

# ---- 3 · Activity Card (Monthly contributions + streaks) ---------------------
def activity(data, theme_name):
    t = THEMES[theme_name]
    h = 340
    monthly = data["monthly"][-12:]
    best = max(monthly[:-1] or monthly, key=lambda m: m["total"])
    top = max(1, best["total"])
    x0, x1, base, maxh, gap = 40, 600, 292, 140, 10
    bw = (x1 - x0 - gap * (len(monthly) - 1)) / len(monthly)
    bars = []
    for i, m in enumerate(monthly):
        partial = i == len(monthly) - 1
        is_best = m is best
        bh = max(4, round(m["total"] / top * maxh))
        x = x0 + i * (bw + gap)
        fill = t["tech"] if is_best else (t["activity_bar_partial"] if partial else t["activity_bar_default"])
        label = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")
        bars.append(
            f'<rect class="g" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x:.1f}" y="{base - bh}" '
            f'width="{bw:.1f}" height="{bh}" rx="4" fill="{fill}"><title>{label}: {m["total"]:,}</title></rect>'
            f'<text class="f" style="animation-delay:{2.2 + i * 0.07:.2f}s" x="{x + bw / 2:.1f}" y="{base + 22}" '
            f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{t["muted"]}">{label}</text>'
        )
        if is_best:
            bars.append(
                f'<text class="p" style="animation-delay:3.2s" x="{x + bw / 2:.1f}" y="{base - bh - 10}" '
                f'text-anchor="middle" font-family="{MONO}" font-size="11" fill="{t["tech"]}">{m["total"]:,}</text>'
            )
    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    streak_note = "current streak & all-time record" if cs >= ls else f"current streak, longest {ls}"
    total_days = len(data["days"])
    stats = [
        (f'{cs} <tspan font-style="italic">days</tspan>', streak_note),
        (f'{data["active_days"]}<tspan fill="{t["muted"]}"> / {total_days}</tspan>', "days with active commits"),
        (f'{data["best_day"]["count"]}', "commits on busiest day"),
    ]
    side = []
    for i, (big, small) in enumerate(stats):
        y = 104 + i * 92
        side.append(
            f'<g class="r" {d(2.6 + i * 0.15)}>'
            f'<text x="650" y="{y}" font-family="{SERIF}" font-size="40" fill="{t["ink"]}">{big}</text>'
            f'<text x="650" y="{y + 24}" font-family="{SANS}" font-size="13" fill="{t["muted"]}">{small}</text></g>'
        )
        if i < 2:
            side.append(f'<rect class="f" {d(2.6)} x="650" y="{y + 44}" width="190" height="1" fill="{t["rule"]}"/>')
    border = f'<rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="14" fill="none" stroke="{t["frame"]}" stroke-width="1"/>' if theme_name == "dark" else ""
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{t['bg']}"/>
{border}
<text class="f" {d(1.9)} x="40" y="58" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{t['muted']}">THE LAST 12 MONTHS ON GITHUB</text>
<text class="r" {d(2.0)} x="38" y="114" font-family="{SERIF}" font-size="52" fill="{t['ink']}">{data["total_contributions"]:,} <tspan font-style="italic">contributions</tspan></text>
{''.join(bars)}
{''.join(side)}
"""
    write(f"activity-{theme_name}.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
          f'{data["total_contributions"]:,} contributions in the last year, {cs}-day streak ({theme_name})'))

# ---- 4 · Blue Contribution Heatmap with User Tagline ------------------------
def level_for(c):
    return 0 if c == 0 else 1 if c <= 5 else 2 if c <= 15 else 3 if c <= 30 else 4 if c <= 50 else 5

def heatmap(data, theme_name):
    t = THEMES[theme_name]
    shades = t["heatmap_shades"]
    days = data["days"]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7
    cell, step, gx, gy = 12, 15, 44, 96
    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        date = datetime.date.fromisoformat(day["date"])
        if date.day <= 7 and (date.year, date.month) not in seen and row == 0:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))
        c = day["count"]
        delay = 1.0 + col * 0.03 + row * 0.02
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="3" fill="{shades[level_for(c)]}">'
            f'<title>{day["date"]}: {c} contribution{"s" if c != 1 else ""}</title></rect>'
        )
    ncols = (len(days) + lead + 6) // 7
    right = gx + ncols * step - 3
    labels = "".join(
        f'<text x="{gx + col * step}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{t["muted"]}">{m}</text>'
        for col, m in months if col < ncols - 12
    )
    legend_x = right - len(shades) * 14
    legend = "".join(
        f'<rect x="{legend_x + i * 14}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2.5" fill="{c}"/>'
        for i, c in enumerate(shades)
    )
    h = gy + 7 * step + 44
    border = f'<rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="14" fill="none" stroke="{t["frame"]}" stroke-width="1"/>' if theme_name == "dark" else ""
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{t['bg']}"/>
{border}
<text class="r" {d(0.8)} x="42" y="62" font-family="{SERIF}" font-size="34" fill="{t['ink']}">Shaping future <tspan font-style="italic" fill="{t['tech']}">through creative code</tspan></text>
<text class="f" {d(0.8)} x="{right}" y="60" text-anchor="end" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{t['muted']}">REFRESHED DAILY</text>
{''.join(cells)}
<g class="f" {d(2.4)}>{labels}
<text x="{legend_x - 8}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{t['muted']}">less</text>
{legend}
<text x="{legend_x + len(shades) * 14 + 2}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{t['muted']}">more</text></g>
"""
    write(f"heatmap-{theme_name}.svg", svg(W, h, body, ["serif", "serif-i", "mono"],
          f'Shaping future through creative code: {data["total_contributions"]:,} contributions ({theme_name})'))

# ---- 5 · Repo Cards & Section Titles ----------------------------------------
REPO_W, REPO_H = 880 / 3 - 8, 176
REPOS = [
    ("sagarithm-kit", "Cross-agent software engineering framework for AI coding agents.", "TypeScript", "tech", 18),
    ("clint", "Automates intelligent lead generation and outreach workflows at scale.", "Python", "studio", 33),
    ("openhuman", "Merged PRs in core agent orchestrator, search tools, and engine traces.", "Rust", "oss", 42621),
]

def repo_card(i, name, desc, lang, color_key, stars, theme_name):
    t = THEMES[theme_name]
    color = t[color_key]
    delay = 4.6 + i * 0.12
    star_str = f"{stars/1000:.1f}k" if stars >= 1000 else str(stars)
    meta = f"{lang}  ·  ★ {star_str}" if stars else f"{lang}  ·  active"
    border = f'<rect x="0.5" y="0.5" width="{REPO_W-1}" height="{REPO_H-1}" rx="14" fill="none" stroke="{t["frame"]}" stroke-width="1"/>' if theme_name == "dark" else ""
    body = f"""
<rect width="{REPO_W}" height="{REPO_H}" rx="14" fill="{t['bg']}"/>
{border}
<g class="r" {d(delay)}>
  <rect x="24" y="30" width="8" height="8" rx="2" fill="{color}"/>
  <text x="40" y="39" font-family="{SANS}" font-weight="600" font-size="18" fill="{t['ink']}">{escape(name)}</text>
  {text_lines(24, 72, wrap(desc, 34), 21, f'font-family="{SANS}" font-size="14" fill="{t["ink_soft"]}"')}
  <text x="24" y="{REPO_H - 24}" font-family="{MONO}" font-size="12" fill="{t['muted']}">{escape(meta)}</text>
</g>
"""
    write(f"repo-{name}-{theme_name}.svg", svg(REPO_W, REPO_H, body, ["sans", "sans-b", "mono"],
          f"{name}: {desc} ({theme_name})", left=4 * i, right=8 - 4 * i))

def section_title(text, italic, theme_name):
    fg = "#e6edf3" if theme_name == "dark" else "#111111"
    body = (
        f'<text class="r" {d(4.4)} x="2" y="46" font-family="{SERIF}" font-size="34" fill="{fg}">{escape(text)} '
        f'<tspan font-style="italic">{escape(italic)}</tspan></text>'
    )
    write(f"title-coding-{theme_name}.svg", svg(W, 64, body, ["serif", "serif-i"], f"{text} {italic}", bottom=0))

if __name__ == "__main__":
    data = json.load(open(DATA, encoding="utf-8"))
    
    for theme_name in ["light", "dark"]:
        t = THEMES[theme_name]
        hero(theme_name)
        tile("build", "BUILD", t["tech"], "#ffffff", "5+", "products",
             "LovieMe, Periodly, Muzify, Clint & Pixartual ecosystem.", 3.1, 0, theme_name, font_size=36)
        tile("oss", "OPEN SOURCE", t["oss"], "#ffffff", "12+", "major repos",
             "Merged in Selenium, Twenty CRM, Cal.com, freeCodeCamp, and OpenHuman.", 3.35, 1, theme_name, font_size=33)
        tile("agent", "AI AGENTS", t["agent"], "#ffffff", "100%", "agentic",
             "Sagarithm-Kit framework, production skills, MCP tooling, and workflows.", 3.6, 2, theme_name, font_size=34)
        activity(data, theme_name)
        for i, (name, desc, lang, color_key, stars) in enumerate(REPOS):
            repo_card(i, name, desc, lang, color_key, stars, theme_name)
        section_title("What I'm", "building & contributing", theme_name)
        heatmap(data, theme_name)

    # Legacy fallback mirrors for direct links
    for name in ["hero", "heatmap", "activity", "build", "oss", "agent",
                 "repo-sagarithm-kit", "repo-clint", "repo-openhuman"]:
        src_f = os.path.join(OUT, f"{name}-dark.svg")
        dst_f = os.path.join(OUT, f"{name}.svg")
        if os.path.exists(src_f):
            with open(src_f, "rb") as rf, open(dst_f, "wb") as wf:
                wf.write(rf.read())
