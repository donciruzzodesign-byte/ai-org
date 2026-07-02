# winedeck カルーセル統合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `~/Desktop/files/` にある自己完結型のワインカルーセルSVG生成ツール（`winedeck.py`/`render.py`/`deck.example.json`）を、`ai-org` リポジトリに `winedeck/` フォルダとして取り込み、`render.py` の出力先デフォルトを既存の週次出力規約（`~/Desktop/CUBOCCI_STUDIO/weekly/{date}-{theme}/`）に合わせる。

**Architecture:** `winedeck.py`（描画エンジン、無変更）と `render.py`（CLIランナー、出力先デフォルトのみ変更）を新規フォルダ `winedeck/` にそのまま移設する。`runner.py` やエージェント定義は一切変更しない、スタンドアロンツールとしての取り込み。

**Tech Stack:** Python 3 標準ライブラリのみ（SVG生成部）。PNG書き出しは任意で `cairosvg`（`requirements.txt` に既存登録済み、変更不要）。

## Global Constraints

- `winedeck.py` の配色・描画ロジック・スライド種別（cover/rows/bullets/timeline/summary）は無変更（spec: 変更しないもの）。
- `deck.example.json` のJSON仕様・フィールドは無変更。
- コーヒー向け配色（PAL拡張）は対象外。
- `runner.py` / `.claude/agents/*.md` / `agents/*.txt` は一切変更しない。
- `requirements.txt` は変更不要（`cairosvg>=2.7.0` 既存）。
- `render.py` の `--outdir` 未指定時デフォルトは `~/Desktop/CUBOCCI_STUDIO/weekly/{date}-wine/carousel/`（`--date` 省略時は実行日）。`--outdir` 明示時はそちらを優先。

---

### Task 1: winedeck エンジン本体とサンプル仕様を配置

**Files:**
- Create: `winedeck/winedeck.py`
- Create: `winedeck/deck.example.json`
- Test: `tests/test_winedeck.py`

**Interfaces:**
- Produces: `winedeck.cover(wine_type, badge, q, answer, subtitle, grape=None, swipe=...) -> str`（SVG文字列）
- Produces: `winedeck.rows_slide(wine_type, eyebrow, title, rows, num=None, total=9, grape=None, closing=None) -> str`
- Produces: `winedeck.bullets_slide(wine_type, eyebrow, title, items, num=None, total=9, grape=None, closing=None) -> str`
- Produces: `winedeck.timeline_slide(wine_type, eyebrow, title, events, num=None, total=9, grape=None, closing=None) -> str`
- Produces: `winedeck.summary_slide(wine_type, title, points, cta=None, sub=None, num=None, total=9, grape=None) -> str`
- Produces: `winedeck.export(slides: list[str], outdir: str, name: str) -> int`（`cairosvg` 依存、svg/png書き出し）
- Produces: `winedeck.PAL: dict`（ワインタイプ→配色。キー: `white/red/spark/rose/orange/sweet/study/grape`）
- Task 2（`render.py`）はこのモジュールを同一ディレクトリから `import winedeck as wd` で消費する。

- [ ] **Step 1: `winedeck/` ディレクトリを作成し `winedeck.py` を書く**

`winedeck/winedeck.py`:
```python
# -*- coding: utf-8 -*-
"""
winedeck.py — ワイン・カルーセル生成エンジン（本プロジェクト標準）
================================================================
背景＝ワインタイプで色分け／ゴールド枠・明朝見出し・ゴシック本文は全タイプ共通。
ブランド表記（CUBOCCI STUDIO 等）は入れない。出力は Illustrator 編集可能な
ライブテキスト SVG（1080×1350 / 4:5）。

使い方（例）:
    import winedeck as wd
    slides = []
    slides.append(wd.cover("red", badge="赤ワイン",
                           q=["長期熟成する", "偉大な赤は？"],
                           answer="ネッビオーロ", subtitle="バローロの主役"))
    slides.append(wd.rows_slide("red", eyebrow="TASTING", title="味わい",
                    rows=[("香り","カシス・すみれ・タール"),
                          ("味わい","高い酸と豊かなタンニン")], num=2, total=9))
    wd.export(slides, "/path/out", "barolo")   # svg/ と png/ に書き出し
"""
import html, os

W, H, M = 1080, 1350, 96
MINCHO = "'Noto Serif CJK JP','Yu Mincho','Hiragino Mincho ProN',serif"
GOTHIC = "'Noto Sans CJK JP','Yu Gothic','Hiragino Sans',sans-serif"

# ---- タイプ別パレット（承認済み・実フィード抽出色ベース）----
# bg1,bg2=背景グラデ / ink=本文 / sub=補助 / accent=見出し(=答え) / gold=金トリム
# frame=枠 / light=明地か / motif=drop|bubbles|none / tag=フッター英字
PAL = {
 "white":  dict(bg1="#F4EEDD", bg2="#E4D6B4", ink="#34291A", sub="#6E5C3C",
                accent="#A6791F", gold="#B8912F", frame="#B8912F", light=True,
                motif="drop", tag="WHITE"),
 "red":    dict(bg1="#4A1220", bg2="#160609", ink="#F3EBDD", sub="#C9BCA6",
                accent="#E7CE86", gold="#C9A24B", frame="#C9A24B", light=False,
                motif="drop", tag="RED"),
 "spark":  dict(bg1="#F8F1D6", bg2="#E7CC84", ink="#4A3A12", sub="#7A6428",
                accent="#B8891E", gold="#B8912F", frame="#B8912F", light=True,
                motif="bubbles", tag="SPARKLING"),
 "rose":   dict(bg1="#F3DBD7", bg2="#E0AAA6", ink="#5A2A30", sub="#8A5058",
                accent="#AE5966", gold="#B07782", frame="#B07782", light=True,
                motif="drop", tag="ROSATO"),
 "orange": dict(bg1="#ECC488", bg2="#C1742E", ink="#47270E", sub="#6E4418",
                accent="#8F3F12", gold="#9C5A1E", frame="#9C5A1E", light=True,
                motif="drop", tag="ORANGE"),
 "sweet":  dict(bg1="#F2D888", bg2="#C6942A", ink="#48360A", sub="#7A5A16",
                accent="#8A5410", gold="#A6791F", frame="#A6791F", light=True,
                motif="drop", tag="DOLCE"),
 "study":  dict(bg1="#1A2C46", bg2="#0A1120", ink="#EAF0F7", sub="#A9BAD2",
                accent="#6BA0E0", gold="#C9A24B", frame="#C9A24B", light=False,
                motif="none", tag="STUDY"),
 "grape":  dict(bg1="#1B1720", bg2="#050406", ink="#F0E9DC", sub="#B8AE9E",
                accent="#C9A24B", gold="#C9A24B", frame="#C9A24B", light=False,
                motif="none", tag="GRAPE"),
}

# ブドウ品種でアクセントを微調整（明地の見出し／暗地の差し色・モチーフに）
GRAPE_ACCENT = {
 "sangiovese": "#B5372E", "nebbiolo": "#8E2B2F", "cabernet": "#5A2E5E",
 "merlot": "#7A2138", "vermentino": "#7E8A3C", "arneis": "#B08C2E",
 "moscato": "#C79A2E", "picolit": "#C69A2B",
}

def esc(s): return html.escape(str(s), quote=True)

def _defs(p, uid):
    return (f'<defs><linearGradient id="bg{uid}" x1="0" y1="0" x2="0.35" y2="1">'
            f'<stop offset="0" stop-color="{p["bg1"]}"/>'
            f'<stop offset="1" stop-color="{p["bg2"]}"/></linearGradient>'
            f'<linearGradient id="gd{uid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{p["gold"]}"/>'
            f'<stop offset="1" stop-color="{p["frame"]}"/></linearGradient></defs>')

def _bg(p, uid):
    return (f'<rect width="{W}" height="{H}" fill="url(#bg{uid})"/>'
            f'<rect x="40" y="40" width="{W-80}" height="{H-80}" fill="none" '
            f'stroke="{p["frame"]}" stroke-opacity="0.6" stroke-width="1.4"/>'
            f'<rect x="48" y="48" width="{W-96}" height="{H-96}" fill="none" '
            f'stroke="{p["frame"]}" stroke-opacity="0.25" stroke-width="0.8"/>')

def _t(x, y, s, size, fill, font=GOTHIC, weight="400", anchor="start", spacing="0", opacity="1"):
    ls = f' letter-spacing="{spacing}"' if spacing != "0" else ""
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls} opacity="{opacity}">{esc(s)}</text>')

def _drop(cx, cy, s, fill, opacity="1"):
    k=s/70.0
    path='M50,15 C50,15 22,48 22,64 a28,28 0 1,0 56,0 C78,48 50,15 50,15 Z'
    return (f'<g transform="translate({cx-50*k},{cy-15*k}) scale({k})" opacity="{opacity}">'
            f'<path d="{path}" fill="{fill}"/></g>')

def _bubbles(cx, cy, accent):
    pts=[(0,0,11),(-24,20,6),(22,24,7),(-12,44,4),(16,50,5),(2,70,9)]
    return "".join(f'<circle cx="{cx+dx}" cy="{cy+dy}" r="{r}" fill="none" '
                   f'stroke="{accent}" stroke-width="2" opacity="0.85"/>' for dx,dy,r in pts)

def _motif(p, cx, cy, s):
    if p["motif"]=="drop":    return _drop(cx, cy, s, f'url(#gd{p["_uid"]})', "0.9")
    if p["motif"]=="bubbles": return _bubbles(cx, cy, p["accent"])
    return ""

def _hair(p, x1, x2, y, op="0.4", w="1.0"):
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{p["gold"]}" '
            f'stroke-opacity="{op}" stroke-width="{w}"/>')

def _eyebrow(p, x, y, label, anchor="start"):
    col = p["accent"] if p["motif"]=="none" and not p["light"] else p["gold"]
    return _t(x, y, label, 24, col, GOTHIC, "500", anchor, spacing="6")

def _footer(p, num, total):
    if num is None: return ""
    y=H-70
    return (_hair(p, M, W-M, y-26, op="0.3") +
            _t(M, y, f'PICOLIT ・ {p["tag"]}' if False else p["tag"], 19, p["gold"], GOTHIC,
               "500", spacing="3", opacity="0.85") +
            _t(W-M, y, f"{num:02d} / {total:02d}", 19, p["sub"], GOTHIC, anchor="end", spacing="2"))

def _svg(p, uid, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">{_defs(p,uid)}{_bg(p,uid)}{body}</svg>')

_UID = [0]
def _prep(wine_type, grape=None):
    p = dict(PAL[wine_type]); _UID[0]+=1; p["_uid"]=_UID[0]
    if grape and grape.lower() in GRAPE_ACCENT:
        g = GRAPE_ACCENT[grape.lower()]
        # 明地は見出しを品種色に、暗地はモチーフ/差し色のみ品種色に（可読性優先）
        if p["light"]: p["accent"]=g
        p["grape_accent"]=g
    return p

# ===================== スライド・ビルダー =====================
def cover(wine_type, badge, q, answer, subtitle, grape=None, swipe="スワイプで解説 →"):
    """表紙。q=質問行のリスト（1〜2行）"""
    p=_prep(wine_type, grape); uid=p["_uid"]; cx=W/2; b=[]
    b.append(_drop(cx, 250, 92, f'url(#gd{uid})') if p["motif"]!="bubbles"
             else _bubbles(cx, 210, p["accent"]))
    # バッジ
    bw=max(150, len(badge)*30+64)
    b.append(f'<rect x="{cx-bw/2}" y="378" width="{bw}" height="46" rx="23" fill="none" '
             f'stroke="{p["accent"]}" stroke-width="1.4"/>')
    b.append(_t(cx, 409, badge, 24, p["accent"], GOTHIC, "600", "middle", spacing="3"))
    # 質問
    qy=520
    for line in q:
        b.append(_t(cx, qy, line, 52, p["ink"], MINCHO, "700", "middle", spacing="2")); qy+=66
    # 答え
    ans=answer; asz = 84 if len(ans)<=6 else (64 if len(ans)<=9 else 46)
    b.append(_t(cx, 800, f"= {ans}", asz, p["accent"], MINCHO, "700", "middle", spacing="2"))
    b.append(_hair(p, cx-190, cx+190, 860, op="0.5"))
    b.append(_t(cx, 930, subtitle, 40, p["ink"], MINCHO, "500", "middle", spacing="3"))
    b.append(_t(cx, H-150, swipe, 26, p["gold"], GOTHIC, "500", "middle", spacing="3"))
    return _svg(p, uid, "".join(b))

def _header(p, eyebrow, title, y_eb=200, y_ti=292, y_hr=342):
    b=[_eyebrow(p, M, y_eb, eyebrow),
       _t(M, y_ti, title, 62, p["ink"], MINCHO, "700", spacing="2"),
       _hair(p, M, W-M, y_hr, op="0.45", w="1.2")]
    return b

def rows_slide(wine_type, eyebrow, title, rows, num=None, total=9, grape=None,
               closing=None):
    """ラベル+値の行スライド。rows=[(label,value), ...]"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    n=len(rows); span=760; y=470; step=min(150, span//max(n,1))
    for label, value in rows:
        b.append(_t(M, y, label, 26, p["gold"], GOTHIC, "600", spacing="2"))
        b.append(_t(M, y+48, value, 32, p["ink"], MINCHO, "500"))
        b.append(_hair(p, M, W-M, y+82, op="0.18", w="0.7"))
        y+=step
    if closing:
        b.append(_t(M, y+40, closing, 30, p["accent"], MINCHO, "600"))
    if p["motif"]!="none": b.append(_motif(p, W-150, 250, 54))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def bullets_slide(wine_type, eyebrow, title, items, num=None, total=9, grape=None,
                  closing=None):
    """箇条書き（見出し+補足の2行×n）。items=[(head, note), ...]"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    n=len(items); y=460; step=min(140, 780//max(n,1))
    for head, note in items:
        b.append(f'<circle cx="{M+8}" cy="{y-10}" r="6" fill="url(#gd{uid})"/>')
        b.append(_t(M+36, y, head, 34, p["accent"] if p["light"] else p["ink"],
                    MINCHO, "600"))
        if note:
            b.append(_t(M+36, y+44, note, 27, p["sub"], GOTHIC))
        y+=step
    if closing:
        b.append(_hair(p, M, W-M, y-6, op="0.3"))
        b.append(_t(M, y+56, closing, 30, p["accent"], MINCHO, "600"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def timeline_slide(wine_type, eyebrow, title, events, num=None, total=9, grape=None,
                   closing=None):
    """年表。events=[(年, 出来事), ...]"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    n=len(events); y=470; step=min(128, 740//max(n,1)); x=M+8
    b.append(f'<line x1="{x}" y1="{y-18}" x2="{x}" y2="{y+(n-1)*step+18}" '
             f'stroke="{p["gold"]}" stroke-opacity="0.4" stroke-width="1.4"/>')
    for yr, ev in events:
        b.append(f'<circle cx="{x}" cy="{y-10}" r="7" fill="url(#gd{uid})"/>')
        b.append(_t(x+40, y, yr, 32, p["accent"], MINCHO, "700"))
        b.append(_t(x+40, y+42, ev, 26, p["ink"], GOTHIC))
        y+=step
    if closing:
        b.append(_hair(p, M, W-M, y-4, op="0.3"))
        b.append(_t(M, y+54, closing, 32, p["accent"], MINCHO, "700"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def summary_slide(wine_type, title, points, cta=None, sub=None, num=None, total=9, grape=None):
    """まとめ（番号付き）+ CTA"""
    p=_prep(wine_type, grape); uid=p["_uid"]; cx=W/2; b=[]
    b.append(_eyebrow(p, cx, 220, "SUMMARY", "middle"))
    b.append(_t(cx, 312, title, 60, p["ink"], MINCHO, "700", "middle", spacing="2"))
    b.append(_hair(p, cx-230, cx+230, 362, op="0.5"))
    y=470; step=min(108, 620//max(len(points),1))
    for i, pt in enumerate(points, 1):
        b.append(_t(M+6, y, f"{i:02d}", 32, p["gold"], MINCHO, "700"))
        b.append(_t(M+84, y, pt, 30, p["ink"], GOTHIC))
        b.append(_hair(p, M, W-M, y+30, op="0.16", w="0.7"))
        y+=step
    if p["motif"]!="none": b.append(_motif(p, cx, y+24, 60))
    if cta:  b.append(_t(cx, y+170, cta, 32, p["accent"], MINCHO, "500", "middle", spacing="2"))
    if sub:  b.append(_t(cx, y+216, sub, 25, p["sub"], GOTHIC, anchor="middle"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

# ===================== 書き出し =====================
def export(slides, outdir, name):
    import cairosvg
    os.makedirs(f"{outdir}/svg", exist_ok=True)
    os.makedirs(f"{outdir}/png", exist_ok=True)
    for i, s in enumerate(slides, 1):
        sp=f"{outdir}/svg/{name}_{i:02d}.svg"
        with open(sp,"w",encoding="utf-8") as f: f.write(s)
        cairosvg.svg2png(url=sp, write_to=f"{outdir}/png/{name}_{i:02d}.png",
                         output_width=540, output_height=675)
    return len(slides)
```

- [ ] **Step 2: `deck.example.json` を書く**

`winedeck/deck.example.json`:
```json
{
  "name": "barolo",
  "wine_type": "red",
  "grape": "nebbiolo",
  "slides": [
    {
      "kind": "cover",
      "badge": "赤ワイン",
      "q": ["長期熟成する", "偉大な赤は？"],
      "answer": "ネッビオーロ",
      "subtitle": "バローロの主役"
    },
    {
      "kind": "timeline",
      "eyebrow": "HISTORY",
      "title": "ネッビオーロの歩み",
      "events": [
        ["nebbia", "「霧」に由来する晩熟品種"],
        ["19C", "バローロが王のワインに"],
        ["現在", "単一畑クリュの時代へ"]
      ],
      "closing": "霧の丘が、高貴な渋みを育てる。"
    },
    {
      "kind": "rows",
      "eyebrow": "REGULATION",
      "title": "バローロDOCG規定",
      "rows": [
        ["最低熟成", "38ヶ月（うち樽18ヶ月）"],
        ["リゼルヴァ", "62ヶ月（うち樽18ヶ月）"],
        ["品種", "ネッビオーロ100%"]
      ],
      "closing": "長期熟成が、この品種の宿命。"
    },
    {
      "kind": "summary",
      "title": "バローロ まとめ",
      "points": [
        "ネッビオーロ100%の長期熟成型",
        "最低38ヶ月（樽18ヶ月）熟成",
        "単一畑クリュで個性が分かれる"
      ],
      "cta": "保存して一本選びに。",
      "sub": "次回はバルバレスコと比較。"
    }
  ]
}
```

- [ ] **Step 3: スモークテストを書く**

`tests/test_winedeck.py`:
```python
import os
import sys

WINEDECK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "winedeck"
)
if WINEDECK_DIR not in sys.path:
    sys.path.insert(0, WINEDECK_DIR)

import winedeck as wd


def test_cover_returns_svg_with_correct_dimensions():
    svg = wd.cover("red", badge="赤ワイン", q=["長期熟成する", "偉大な赤は？"],
                    answer="ネッビオーロ", subtitle="バローロの主役", grape="nebbiolo")
    assert svg.startswith("<svg")
    assert 'width="1080"' in svg
    assert 'height="1350"' in svg
    assert "ネッビオーロ" in svg


def test_rows_slide_includes_all_rows_and_footer():
    svg = wd.rows_slide("red", "REGULATION", "バローロDOCG規定",
                         [("最低熟成", "38ヶ月（うち樽18ヶ月）"), ("品種", "ネッビオーロ100%")],
                         num=2, total=3, grape="nebbiolo")
    assert "最低熟成" in svg
    assert "38ヶ月（うち樽18ヶ月）" in svg
    assert "02 / 03" in svg


def test_summary_slide_includes_points_and_cta():
    svg = wd.summary_slide("red", "バローロ まとめ",
                            ["ネッビオーロ100%の長期熟成型", "最低38ヶ月（樽18ヶ月）熟成"],
                            cta="保存して一本選びに。", num=3, total=3)
    assert "バローロ まとめ" in svg
    assert "保存して一本選びに。" in svg


def test_unknown_wine_type_raises_keyerror():
    import pytest
    with pytest.raises(KeyError):
        wd.cover("nonexistent", badge="x", q=["a"], answer="b", subtitle="c")
```

- [ ] **Step 4: テスト実行**

Run: `python3 -m pytest tests/test_winedeck.py -v`
Expected: 4 passed

- [ ] **Step 5: コミット**

```bash
git add winedeck/winedeck.py winedeck/deck.example.json tests/test_winedeck.py
git commit -m "$(cat <<'EOF'
feat: add winedeck carousel SVG engine

Bring in the standalone wine-type-colored Instagram carousel
generator (cover/rows/bullets/timeline/summary slide builders)
as winedeck/winedeck.py, unchanged from its source.
EOF
)"
```

---

### Task 2: render.py CLIランナーと出力先デフォルトの実装

**Files:**
- Create: `winedeck/render.py`
- Test: `tests/test_winedeck_render.py`

**Interfaces:**
- Consumes: `winedeck.py` の `PAL`, `cover`, `rows_slide`, `bullets_slide`, `timeline_slide`, `summary_slide`, `export`（Task 1、同一ディレクトリから `import winedeck as wd`）
- Produces: `resolve_outdir(date_str: str, base_dir: str = WEEKLY_BASE_DIR) -> str`
- Produces: `WEEKLY_BASE_DIR: str`（`~/Desktop/CUBOCCI_STUDIO/weekly`）
- Produces: CLI（`python winedeck/render.py <spec.json> [--outdir DIR] [--date YYYY-MM-DD] [--svg-only]`）

- [ ] **Step 1: `render.py` を書く（出力先デフォルトロジックを追加）**

`winedeck/render.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render.py — JSONのデッキ仕様から カルーセルSVG/PNG を書き出すデータ駆動ランナー。

使い方:
    python render.py deck.example.json
    python render.py deck.json --outdir ./out --svg-only
    python render.py deck.json --date 2026-07-06
        # --outdir省略時: ~/Desktop/CUBOCCI_STUDIO/weekly/2026-07-06-wine/carousel/

JSON仕様（deck.example.json 参照）:
{
  "name": "barolo",
  "wine_type": "red",          # デッキ既定のタイプ（各スライドで上書き可）
  "grape": "nebbiolo",          # デッキ既定の品種アクセント（任意・上書き可）
  "slides": [
    {"kind": "cover", "badge": "...", "q": ["..",".."], "answer": "..", "subtitle": ".."},
    {"kind": "rows", "eyebrow": "..", "title": "..", "rows": [["ラベル","値"], ...], "closing": ".."},
    {"kind": "bullets", "eyebrow": "..", "title": "..", "items": [["見出し","補足"], ...]},
    {"kind": "timeline", "eyebrow": "..", "title": "..", "events": [["年","出来事"], ...]},
    {"kind": "summary", "title": "..", "points": ["..",".."], "cta": "..", "sub": ".."}
  ]
}

注意:
- 日本語は自動折り返ししません。1行の目安は下記 LIMITS 参照（超過すると警告を出します）。
- num/total は並び順から自動採番（cover にはフッター無し）。
- --outdir 省略時のデフォルトは ~/Desktop/CUBOCCI_STUDIO/weekly/{--date}-wine/carousel/
  （--date 省略時は実行日）。--outdir を明示すればそちらを優先。
"""
import sys, json, argparse, os, datetime
import winedeck as wd

# 1行あたりの全角換算・目安（枠内に収まる上限の実測ベース）
LIMITS = {
    "q": 12, "answer": 12, "subtitle": 16,        # cover
    "title": 13, "value": 26, "note": 30,         # 中面
    "event": 26, "point": 24, "head": 18,
}

DESKTOP_DIR = os.path.expanduser("~/Desktop/CUBOCCI_STUDIO")
WEEKLY_BASE_DIR = os.path.join(DESKTOP_DIR, "weekly")


def resolve_outdir(date_str, base_dir=WEEKLY_BASE_DIR):
    """--outdir未指定時のデフォルト出力先（wineテーマ固定、carouselサブフォルダ）。"""
    return os.path.join(base_dir, f"{date_str}-wine", "carousel")


def warn(msg): print(f"[warn] {msg}", file=sys.stderr)

def _check_len(field, text, limit):
    # 全角=1, 半角≈0.5 の粗い換算
    wlen = sum(1 if ord(c) > 0x2E7F else 0.5 for c in str(text))
    if wlen > limit:
        warn(f'{field}: 長すぎる可能性（目安{limit} / 実測{wlen:.0f}）→ "{text}"')

def build(spec):
    name = spec.get("name", "deck")
    dtype = spec.get("wine_type", "red")
    dgrape = spec.get("grape")
    raw = spec["slides"]
    total = len(raw)
    slides = []
    for i, s in enumerate(raw, 1):
        kind = s["kind"]
        wt = s.get("wine_type", dtype)
        grape = s.get("grape", dgrape)
        if kind == "cover":
            for q in s.get("q", []): _check_len("q", q, LIMITS["q"])
            _check_len("answer", s["answer"], LIMITS["answer"])
            _check_len("subtitle", s.get("subtitle",""), LIMITS["subtitle"])
            slides.append(wd.cover(wt, badge=s["badge"], q=s["q"], answer=s["answer"],
                                   subtitle=s.get("subtitle",""), grape=grape,
                                   swipe=s.get("swipe", "スワイプで解説 →")))
        elif kind == "rows":
            _check_len("title", s["title"], LIMITS["title"])
            for _, v in s["rows"]: _check_len("value", v, LIMITS["value"])
            slides.append(wd.rows_slide(wt, s["eyebrow"], s["title"],
                          [tuple(r) for r in s["rows"]], num=i, total=total,
                          grape=grape, closing=s.get("closing")))
        elif kind == "bullets":
            _check_len("title", s["title"], LIMITS["title"])
            for h, n in s["items"]:
                _check_len("head", h, LIMITS["head"]); _check_len("note", n, LIMITS["note"])
            slides.append(wd.bullets_slide(wt, s["eyebrow"], s["title"],
                          [tuple(x) for x in s["items"]], num=i, total=total,
                          grape=grape, closing=s.get("closing")))
        elif kind == "timeline":
            for _, e in s["events"]: _check_len("event", e, LIMITS["event"])
            slides.append(wd.timeline_slide(wt, s["eyebrow"], s["title"],
                          [tuple(e) for e in s["events"]], num=i, total=total,
                          grape=grape, closing=s.get("closing")))
        elif kind == "summary":
            for pt in s["points"]: _check_len("point", pt, LIMITS["point"])
            slides.append(wd.summary_slide(wt, s["title"], s["points"],
                          cta=s.get("cta"), sub=s.get("sub"), num=i, total=total, grape=grape))
        else:
            raise ValueError(f"unknown kind: {kind}")
    return name, slides

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--outdir", default=None,
                    help="省略時は ~/Desktop/CUBOCCI_STUDIO/weekly/{--date}-wine/carousel/")
    ap.add_argument("--date", default=datetime.date.today().isoformat(),
                    help="--outdir省略時の週次フォルダの日付（YYYY-MM-DD、既定: 実行日）")
    ap.add_argument("--svg-only", action="store_true")
    args = ap.parse_args()
    outdir = args.outdir if args.outdir is not None else resolve_outdir(args.date)
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    name, slides = build(spec)
    if args.svg_only:
        os.makedirs(f"{outdir}/svg", exist_ok=True)
        for i, s in enumerate(slides, 1):
            with open(f"{outdir}/svg/{name}_{i:02d}.svg", "w", encoding="utf-8") as f:
                f.write(s)
        print(f"wrote {len(slides)} SVG to {outdir}/svg")
    else:
        n = wd.export(slides, outdir, name)
        print(f"wrote {n} slides (svg+png) to {outdir}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: CLI統合テストを書く（`--svg-only` で cairosvg 不要のまま検証）**

`tests/test_winedeck_render.py`:
```python
import os
import subprocess
import sys

WINEDECK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "winedeck"
)
RENDER_PATH = os.path.join(WINEDECK_DIR, "render.py")
DECK_EXAMPLE_PATH = os.path.join(WINEDECK_DIR, "deck.example.json")


def test_cli_default_outdir_lands_under_desktop_weekly_carousel(tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    env = {**os.environ, "HOME": str(fake_home)}
    result = subprocess.run(
        [sys.executable, RENDER_PATH, DECK_EXAMPLE_PATH, "--date", "2026-07-06", "--svg-only"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    svg_dir = fake_home / "Desktop" / "CUBOCCI_STUDIO" / "weekly" / "2026-07-06-wine" / "carousel" / "svg"
    files = sorted(os.listdir(svg_dir))
    assert files == ["barolo_01.svg", "barolo_02.svg", "barolo_03.svg", "barolo_04.svg"]


def test_cli_explicit_outdir_overrides_default(tmp_path):
    outdir = tmp_path / "custom"
    result = subprocess.run(
        [sys.executable, RENDER_PATH, DECK_EXAMPLE_PATH, "--outdir", str(outdir), "--svg-only"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert os.path.exists(os.path.join(str(outdir), "svg", "barolo_01.svg"))
```

- [ ] **Step 3: テスト実行**

Run: `python3 -m pytest tests/test_winedeck_render.py -v`
Expected: 2 passed

- [ ] **Step 4: コミット**

```bash
git add winedeck/render.py tests/test_winedeck_render.py
git commit -m "$(cat <<'EOF'
feat: add winedeck render.py CLI with Desktop weekly output default

--outdir now defaults to
~/Desktop/CUBOCCI_STUDIO/weekly/{--date}-wine/carousel/,
matching the express-agent's existing weekly output convention.
Explicit --outdir still overrides.
EOF
)"
```

---

### Task 3: README とドキュメント整備

**Files:**
- Create: `winedeck/README.md`

**Interfaces:**
- Consumes: Task 1/2 で確定した実際のファイル構成・CLI引数（`--outdir`, `--date`, `--svg-only`）
- Produces: なし（ドキュメントのみ）

- [ ] **Step 1: `winedeck/README.md` を書く**

`winedeck/README.md`:
```markdown
# winedeck — ワイン・カルーセル生成エンジン（Claude Code 連携用）

背景＝ワインタイプで色分け／ゴールド枠・明朝見出し・ゴシック本文は全タイプ共通。
出力は **Illustrator編集可能なライブテキストSVG（1080×1350 / 4:5）** ＋ 任意でPNGプレビュー。
ブランド表記（CUBOCCI STUDIO 等）は入れない方針。

## 構成
```
winedeck.py          エンジン本体（パレット＋描画プリミティブ＋スライドビルダー）
render.py            JSON仕様 → SVG/PNG のデータ駆動ランナー（CLI）
deck.example.json    デッキ仕様のサンプル（バローロ）
```
依存は `requirements.txt`（リポジトリ直下）の `cairosvg` のみ、かつPNGを焼く時だけ必要。

## セットアップ
```bash
# 1) Python 依存（リポジトリ直下から）
pip install -r requirements.txt

# 2) cairosvg 用の system Cairo（PNGを焼く場合のみ）
#   macOS:
brew install cairo pango gdk-pixbuf libffi
```

### フォント（重要）
SVGは次のフォールバック順で指定：
- 見出し（明朝）: `Noto Serif CJK JP` → `Yu Mincho` → `Hiragino Mincho ProN`
- 本文（ゴシック）: `Noto Sans CJK JP` → `Yu Gothic` → `Hiragino Sans`

- **Illustratorで開く**：macOSなら游書体・ヒラギノで自動解決。確定フォントに揃えたい場合はAI側で置換してからアウトライン化。
- **PNGを焼く（cairosvg）**：その環境に上記CJKフォントのいずれかが必要。無いと日本語が豆腐(□)になる。

## 使い方：CLI（データ駆動・推奨）

リポジトリ直下から実行する。

```bash
# デフォルト：~/Desktop/CUBOCCI_STUDIO/weekly/{実行日}-wine/carousel/ に svg+png
python winedeck/render.py winedeck/deck.example.json

# --date を指定して特定週のフォルダへ
python winedeck/render.py winedeck/deck.example.json --date 2026-07-06

# --outdir を明示すればそちらを優先（依存なしで動く --svg-only も可）
python winedeck/render.py winedeck/deck.example.json --outdir ./out --svg-only
```
出力：`<outdir>/svg/<name>_NN.svg`, `<outdir>/png/<name>_NN.png`

## 使い方：ライブラリとして
```python
import sys, os
sys.path.insert(0, "winedeck")
import winedeck as wd

slides = [
    wd.cover("red", badge="赤ワイン", q=["長期熟成する","偉大な赤は？"],
             answer="ネッビオーロ", subtitle="バローロの主役", grape="nebbiolo"),
    wd.rows_slide("red", "REGULATION", "バローロDOCG規定",
        [("最低熟成","38ヶ月（うち樽18ヶ月）"), ("品種","ネッビオーロ100%")],
        num=2, total=3, grape="nebbiolo"),
    wd.summary_slide("red", "まとめ", ["100%ネッビオーロ","最低38ヶ月熟成"],
        cta="保存して一本選びに。", num=3, total=3),
]
wd.export(slides, "./out", "barolo")     # PNGも要る場合
```

## ワインタイプ（背景キー）
`white / red / spark / rose / orange / sweet / study / grape`
- 明地（white, spark, rose, orange, sweet）＝文字は濃色
- 暗地（red, study, grape）＝文字はクリーム
- `study`＝学び・格付け・歴史（ネイビー）、`grape`＝品種・構造（チャコール黒）

## 品種アクセント
`grape="sangiovese"` のように指定すると、`GRAPE_ACCENT`（winedeck.py内）の色で
- 明地：見出し（=答え）の色を品種色に
- 暗地：可読性優先でモチーフ/差し色に品種色を使い、見出しはゴールド維持

登録済み：sangiovese / nebbiolo / cabernet / merlot / vermentino / arneis / moscato / picolit。
品種追加は `GRAPE_ACCENT` に1行足すだけ。コーヒー向け配色は未対応（対象外）。

## JSON仕様（deck.example.json 参照）
トップ：`name`, `wine_type`（既定）, `grape`（既定・任意）, `slides[]`
各スライド `kind`：
| kind | 主なフィールド |
|------|----------------|
| cover | badge, q[1〜2行], answer, subtitle, (grape, swipe) |
| rows | eyebrow, title, rows[[label,value]...], (closing) |
| bullets | eyebrow, title, items[[head,note]...], (closing) |
| timeline | eyebrow, title, events[[year,event]...], (closing) |
| summary | title, points[...], (cta, sub) |
- 各スライドで `wine_type` / `grape` を指定すればデッキ既定を上書き。
- `num`/`total` は並び順から自動採番（cover はフッター無し）。

## 制約と運用ルール（要遵守）
1. **日本語の自動折り返しは無い**。長文は呼び出し側で改行・分割する。`render.py` は
   1行の目安を超えると `[warn]` を出す（目安：見出し13・値26・補足30・答え12全角程度）。
2. **出力サイズは 1080×1350 固定**（`winedeck.py` 冒頭 `W,H,M`）。
3. 各SVGの内部ID（グラデ等）は呼び出しごとに一意化済み。1ファイル1枚で使う前提。
4. スタンドアロンツールとして統合済み（`runner.py` への自動組み込みは無し）。
   毎週の実行はオーナーが手動で `python winedeck/render.py <deck.json> --date <週の日付>` を叩く運用。
```

- [ ] **Step 2: `--svg-only` で手動動作確認（cairosvgのsystem Cairoが無い環境でも動くことを確認）**

Run: `python3 winedeck/render.py winedeck/deck.example.json --outdir /tmp/winedeck-check --svg-only`
Expected: `wrote 4 SVG to /tmp/winedeck-check/svg` と表示され、`/tmp/winedeck-check/svg/barolo_01.svg`〜`barolo_04.svg` が生成される。

- [ ] **Step 3: 全体テスト実行**

Run: `python3 -m pytest tests/test_winedeck.py tests/test_winedeck_render.py -v`
Expected: 6 passed

- [ ] **Step 4: コミット**

```bash
git add winedeck/README.md
git commit -m "$(cat <<'EOF'
docs: add winedeck/README.md for new repo location

Documents the winedeck/ folder layout, the new Desktop
weekly-carousel output default, and CLI usage from the repo root.
EOF
)"
```
