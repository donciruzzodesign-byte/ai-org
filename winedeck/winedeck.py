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
