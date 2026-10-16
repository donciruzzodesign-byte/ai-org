# -*- coding: utf-8 -*-
"""香りシリーズ共通：フラットSVGアイコン生成ヘルパー。
各回のアイコン生成スクリプトから import して使う（winedeck本体には依存しない独立ユーティリティ）。
"""

def grad(uid, stops):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<radialGradient id="g{uid}" cx="0.35" cy="0.3" r="0.8">{s}</radialGradient>'

def leaf(x, y, rot, fill="#6E8F3A", scale=1.0):
    return (f'<g transform="translate({x},{y}) rotate({rot}) scale({scale})">'
            f'<path d="M0,0 C 18,-6 30,-22 14,-34 C -2,-22 -10,-8 0,0 Z" fill="{fill}"/></g>')

def stem(x1, y1, x2, y2, w=5, color="#5A3A22"):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>'

def cluster(cx, cy, fill, n=7, r=22, spread=56):
    layout = [(0,-1.0),(-0.85,-0.3),(0.85,-0.3),(-0.5,0.55),(0.5,0.55),(0,0.15),(-0.95,0.4),(0.95,0.4)]
    out = ""
    for dx, dy in layout[:n]:
        x = cx + dx*spread
        y = cy + dy*spread
        out += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"/>'
        out += f'<circle cx="{x-r*0.3:.1f}" cy="{y-r*0.3:.1f}" r="{r*0.3:.1f}" fill="#ffffff" opacity="0.22"/>'
    return out

def petals(cx, cy, n, rx, ry, reach, fill, center_fill="#E8C84C", center_r=12):
    import math
    out = "".join(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" '
        f'transform="rotate({i*360/n} {cx} {cy}) translate(0,{-reach})"/>'
        for i in range(n)
    )
    out += f'<circle cx="{cx}" cy="{cy}" r="{center_r}" fill="{center_fill}"/>'
    return out

# ---- バッジ大（400x400、背景circle付き）----
BIG_S = 400; BIG_C = BIG_S / 2

def big_backdrop(fill, ring, r=188):
    return (f'<circle cx="{BIG_C}" cy="{BIG_C}" r="{r}" fill="{fill}"/>'
            f'<circle cx="{BIG_C}" cy="{BIG_C}" r="{r}" fill="none" stroke="{ring}" stroke-width="3" opacity="0.65"/>')

def big_wrap(body, fill, ring, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{BIG_S}" height="{BIG_S}" viewBox="0 0 {BIG_S} {BIG_S}">'
            f'<defs>{defs}</defs>{big_backdrop(fill, ring)}{body}</svg>')

# ---- ミニアイコン（160x160、背景なし透過）----
MINI_S = 160; MINI_C = MINI_S / 2

def mini_wrap(body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{MINI_S}" height="{MINI_S}" viewBox="0 0 {MINI_S} {MINI_S}">'
            f'<defs>{defs}</defs>{body}</svg>')

import os, subprocess

def render_pngs(svg_dir, png_dir, size, venv_python="/Users/kubotahironori/ai-org/.render_venv/bin/python3"):
    os.makedirs(png_dir, exist_ok=True)
    code = (
        "import cairosvg, glob, os\n"
        f"for f in glob.glob({svg_dir!r} + '/*.svg'):\n"
        "    n = os.path.splitext(os.path.basename(f))[0]\n"
        f"    cairosvg.svg2png(url=f, write_to=os.path.join({png_dir!r}, n+'.png'), "
        f"output_width={size}, output_height={size})\n"
    )
    subprocess.run([venv_python, "-c", code], check=True)
