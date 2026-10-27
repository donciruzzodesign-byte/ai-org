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
# ink（本文文字色）は視認性統一のため二値化：明地=濃いグレー、暗地=白
INK_LIGHT = "#2B2B2B"
INK_DARK = "#F5F5F0"

PAL = {
 "white":  dict(bg1="#F4EEDD", bg2="#E4D6B4", ink=INK_LIGHT, sub="#6E5C3C",
                accent="#A6791F", gold="#B8912F", frame="#B8912F", light=True,
                motif="drop", tag="WHITE"),
 "red":    dict(bg1="#4A1220", bg2="#160609", ink=INK_DARK, sub="#C9BCA6",
                accent="#E7CE86", gold="#C9A24B", frame="#C9A24B", light=False,
                motif="drop", tag="RED"),
 "spark":  dict(bg1="#F8F1D6", bg2="#E7CC84", ink=INK_LIGHT, sub="#7A6428",
                accent="#B8891E", gold="#B8912F", frame="#B8912F", light=True,
                motif="bubbles", tag="SPARKLING"),
 "rose":   dict(bg1="#F3DBD7", bg2="#E0AAA6", ink=INK_LIGHT, sub="#8A5058",
                accent="#AE5966", gold="#B07782", frame="#B07782", light=True,
                motif="drop", tag="ROSATO"),
 "orange": dict(bg1="#ECC488", bg2="#C1742E", ink=INK_LIGHT, sub="#6E4418",
                accent="#8F3F12", gold="#9C5A1E", frame="#9C5A1E", light=True,
                motif="drop", tag="ORANGE"),
 "sweet":  dict(bg1="#F2D888", bg2="#C6942A", ink=INK_LIGHT, sub="#7A5A16",
                accent="#8A5410", gold="#A6791F", frame="#A6791F", light=True,
                motif="drop", tag="DOLCE"),
 "study":  dict(bg1="#1A2C46", bg2="#0A1120", ink=INK_DARK, sub="#A9BAD2",
                accent="#6BA0E0", gold="#C9A24B", frame="#C9A24B", light=False,
                motif="none", tag="STUDY"),
 "grape":  dict(bg1="#1B1720", bg2="#050406", ink=INK_DARK, sub="#B8AE9E",
                accent="#C9A24B", gold="#C9A24B", frame="#C9A24B", light=False,
                motif="none", tag="GRAPE"),
 # ワインタイプに紐づかない汎用インフォグラフィック用（CUBOCCI STUDIO ブランドカラー）
 # 2026-10: 「視覚のきほん」参考アカウント準拠に改訂。クリーム×ゴールドのみ、ワインレッドは使わない。
 "brand":  dict(bg1="#F7F2E4", bg2="#EFE4CB", ink=INK_LIGHT, sub="#8A7A5E",
                accent="#A6791F", gold="#C9A84C", frame="#C9A84C", light=True,
                motif="none", tag="CUBOCCI"),
 # 表紙・締め用のダークグリーン（"brand"の本文クリームと対で使う。cover/summaryスライドでwine_type上書き）
 "classic": dict(bg1="#2A3B23", bg2="#0F170B", ink=INK_DARK, sub="#C9BCA0",
                accent="#E3C76B", gold="#C9A84C", frame="#C9A84C", light=False,
                motif="none", tag="CLASSIC"),
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
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W}" height="{H}" '
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
def cover(wine_type, badge, q, answer, subtitle, grape=None, swipe="スワイプで解説 →",
         bottle_photo=None, prefix="= "):
    """表紙。q=質問行のリスト（1〜2行）。
    bottle_photo=ワインボトル写真のdata URI（任意）。指定時はボトル写真をスライド中央に
    大きく配置するヒーローレイアウトになる（バッジ・質問は上、答え・副題は下）。
    未指定時は従来のドロップ/バブル装飾＋テキスト縦積みレイアウト。
    prefix=答えの前に付ける記号（既定 "= "。診断タイトルなど不要な場合は ""）。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; cx=W/2; b=[]
    if bottle_photo:
        badge_w=max(150, len(badge)*30+64)
        b.append(f'<rect x="{cx-badge_w/2}" y="118" width="{badge_w}" height="46" rx="23" fill="none" '
                 f'stroke="{p["accent"]}" stroke-width="1.4"/>')
        b.append(_t(cx, 149, badge, 24, p["accent"], GOTHIC, "600", "middle", spacing="3"))
        qy=232
        for line in q:
            b.append(_t(cx, qy, line, 40, p["ink"], MINCHO, "700", "middle", spacing="2")); qy+=52
        bw, bh = 300, 580
        by = 350
        b.append(_img(cx-bw/2, by, bw, bh, bottle_photo, uid, "bottle", rx=16))
        b.append(f'<rect x="{cx-bw/2}" y="{by}" width="{bw}" height="{bh}" rx="16" fill="none" '
                 f'stroke="{p["frame"]}" stroke-width="1.4" stroke-opacity="0.65"/>')
        ans=answer; asz = 64 if len(ans)<=6 else (52 if len(ans)<=9 else 40)
        ay = by+bh+80
        b.append(_t(cx, ay, f"{prefix}{ans}", asz, p["accent"], MINCHO, "700", "middle", spacing="2"))
        b.append(_hair(p, cx-190, cx+190, ay+42, op="0.5"))
        b.append(_t(cx, ay+96, subtitle, 32, p["ink"], MINCHO, "500", "middle", spacing="2"))
        b.append(_t(cx, H-90, swipe, 24, p["gold"], GOTHIC, "500", "middle", spacing="3"))
        return _svg(p, uid, "".join(b))

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
    b.append(_t(cx, 800, f"{prefix}{ans}", asz, p["accent"], MINCHO, "700", "middle", spacing="2"))
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

def _img(x, y, w, h, href, uid, tag, rx=8):
    """角丸クリップ付き画像。href は data URI（base64）を想定。"""
    if not href:
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                f'fill="#808080" fill-opacity="0.12" stroke="#808080" stroke-opacity="0.35" '
                f'stroke-width="1.2" stroke-dasharray="4,3"/>')
    cid = f"clip{uid}_{tag}"
    return (f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></clipPath>'
            f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="{href}" xlink:href="{href}" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>')

def profile_slide(wine_type, eyebrow, name_it, name_kana, grape_photo, origin_lines,
                  feature_lines, local, jp, num=None, total=9, grape=None):
    """品種プロファイル1枚完結カード。
    grape_photo = data URI（任意）
    origin_lines / feature_lines = 短文のリスト（各1〜2行、自動折り返し無し）
    local / jp = {"name":.., "note":.., "photo": data URI（任意）}
    """
    p=_prep(wine_type, grape); uid=p["_uid"]; b=[]
    b.append(_eyebrow(p, M, 128, eyebrow))

    photo_y, photo_h = 152, 328
    b.append(_img(M, photo_y, W-2*M, photo_h, grape_photo, uid, "grape", rx=6))
    b.append(f'<rect x="{M}" y="{photo_y}" width="{W-2*M}" height="{photo_h}" fill="none" '
             f'stroke="{p["frame"]}" stroke-width="1.2" stroke-opacity="0.6" rx="6"/>')

    name_y = photo_y + photo_h + 62
    b.append(_t(M, name_y, name_it, 50, p["ink"], MINCHO, "700"))
    b.append(_t(M, name_y+38, name_kana, 25, p["sub"], GOTHIC, "500", spacing="2"))

    hy = name_y + 66
    b.append(_hair(p, M, W-M, hy, op="0.4"))

    oy = hy + 38
    b.append(_t(M, oy, "由来", 19, p["gold"], GOTHIC, "600", spacing="2"))
    for i, line in enumerate(origin_lines[:2]):
        b.append(_t(M, oy+32+i*31, line, 24, p["ink"], GOTHIC))

    fy = oy + 32 + 2*31 + 28
    b.append(_t(M, fy, "特徴", 19, p["gold"], GOTHIC, "600", spacing="2"))
    for i, line in enumerate(feature_lines[:2]):
        b.append(_t(M, fy+32+i*31, line, 24, p["ink"], GOTHIC))

    th = 128
    py = fy + 32 + 2*31 + 36
    tx = M + th + 26
    col_w = (W - M) - tx
    b.append(_img(M, py, th, th, local.get("photo"), uid, "local"))
    b.append(_t(tx, py+28, "現地ペアリング", 18, p["gold"], GOTHIC, "600", spacing="1"))
    b.append(_t(tx, py+62, local["name"], 27, p["ink"], MINCHO, "600"))
    b.append(_t(tx, py+94, local["note"], 21, p["sub"], GOTHIC))

    py2 = py + th + 30
    b.append(_img(M, py2, th, th, jp.get("photo"), uid, "jp"))
    b.append(_t(tx, py2+28, "日本食ペアリング", 18, p["gold"], GOTHIC, "600", spacing="1"))
    b.append(_t(tx, py2+62, jp["name"], 27, p["ink"], MINCHO, "600"))
    b.append(_t(tx, py2+94, jp["note"], 21, p["sub"], GOTHIC))

    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def bullets_slide(wine_type, eyebrow, title, items, num=None, total=9, grape=None,
                  closing=None):
    """箇条書き（見出し+補足の2行×n）。items=[(head, note), ...] または
    items=[(head, note, icon), ...]（icon=data URI、任意。無い項目は従来通り丸ポイント）。
    icon指定時はアイコンを主役級サイズ（96px）で表示し、テキストブロックに対して縦中央揃えにする。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    n=len(items); y=460; step=min(140, 780//max(n,1))
    has_any_icon = any(len(it) >= 3 and it[2] for it in items)
    isz = 96 if has_any_icon else 48
    icon_top = -38 if has_any_icon else -34  # y起点からのアイコン上端オフセット（テキストブロックに対し縦中央寄せ）
    for idx, it in enumerate(items):
        head, note = it[0], it[1]
        icon = it[2] if len(it) >= 3 else None
        if icon:
            b.append(_img(M, y+icon_top, isz, isz, icon, uid, f"bl{idx}", rx=14))
            b.append(f'<rect x="{M}" y="{y+icon_top}" width="{isz}" height="{isz}" rx="14" '
                     f'fill="none" stroke="{p["frame"]}" stroke-width="1" stroke-opacity="0.5"/>')
            tx = M + isz + 26
        elif has_any_icon:
            # 同スライド内にアイコン項目がある場合はテキスト開始位置を揃える
            b.append(f'<circle cx="{M+isz/2}" cy="{y-10}" r="9" fill="url(#gd{uid})"/>')
            tx = M + isz + 26
        else:
            b.append(f'<circle cx="{M+8}" cy="{y-10}" r="6" fill="url(#gd{uid})"/>')
            tx = M + 36
        b.append(_t(tx, y, head, 34, p["accent"] if p["light"] else p["ink"],
                    MINCHO, "600"))
        if note:
            b.append(_t(tx, y+44, note, 27, p["sub"], GOTHIC))
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

def summary_slide(wine_type, title, points, cta=None, sub=None, num=None, total=9, grape=None,
                  icon=None):
    """まとめ（番号付き）+ CTA。icon=data URI（任意）。指定時はモチーフの代わりに
    まとめを象徴するイラストアイコンを表示（motif="none"のbrandタイプでも使える）。"""
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
    cta_y, sub_y = y+170, y+216
    if icon:
        isz=180  # スライドの視覚的な主役になるサイズ（従来110pxから拡大）
        icon_y0 = y+14
        b.append(_img(cx-isz/2, icon_y0, isz, isz, icon, uid, "sicon", rx=22))
        b.append(f'<rect x="{cx-isz/2}" y="{icon_y0}" width="{isz}" height="{isz}" rx="22" '
                 f'fill="none" stroke="{p["frame"]}" stroke-width="1.4" stroke-opacity="0.6"/>')
        cta_y = icon_y0 + isz + 50
        sub_y = cta_y + 46
    elif p["motif"]!="none":
        b.append(_motif(p, cx, y+24, 60))
    if cta:  b.append(_t(cx, cta_y, cta, 32, p["accent"], MINCHO, "500", "middle", spacing="2"))
    if sub:  b.append(_t(cx, sub_y, sub, 25, p["sub"], GOTHIC, anchor="middle"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def icon_grid_slide(wine_type, eyebrow, title, items, cols=2, num=None, total=9, grape=None,
                    closing=None):
    """アイコン（またはナンバー）を各セル上部に大きく配置し、見出し・補足をその下に
    縦積みする「画像が主役」のグリッド（要素解説・比較カード向け）。
    items=[(head, note), ...] または items=[(head, note, icon), ...]
    （icon=data URI、任意。1枚でもiconを含む項目があれば全項目を縦積みレイアウトに揃える。
    iconが無い項目は代わりに同サイズのナンバーサークルを表示）。
    note は1行想定（自動折り返し無し）。
    アイコンサイズの目安：cols=1なら180〜220px、cols=2以上ならカラム幅に応じて120〜160px。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    n=len(items); rows=(n+cols-1)//cols
    top, bottom = 380, H-180
    row_h = (bottom-top)//max(rows,1); col_w = (W-2*M)//cols
    has_any_icon = any(len(it) >= 3 and it[2] for it in items)
    badge_ink = INK_LIGHT

    if has_any_icon:
        # 縦積みレイアウト：アイコン/ナンバーが上、見出し・補足がその下
        reserve = 88  # アイコン下端〜行末（見出し+補足+余白）に確保する高さ
        if cols == 1:
            isz = max(150, min(220, row_h - reserve))
        else:
            isz = max(110, min(160, col_w - 40, row_h - reserve))
        for idx, it in enumerate(items):
            head, note = it[0], it[1]
            icon = it[2] if len(it) >= 3 else None
            col, row = idx % cols, idx // cols
            cell_x, cell_y = M+col*col_w, top+row*row_h
            cell_cx = cell_x + col_w/2
            icon_x = cell_cx - isz/2
            if icon:
                b.append(_img(icon_x, cell_y, isz, isz, icon, uid, f"icg{idx}", rx=16))
                b.append(f'<rect x="{icon_x}" y="{cell_y}" width="{isz}" height="{isz}" rx="16" '
                         f'fill="none" stroke="{p["frame"]}" stroke-width="1.2" stroke-opacity="0.55"/>')
            else:
                b.append(f'<circle cx="{cell_cx}" cy="{cell_y+isz/2}" r="{isz/2}" fill="url(#gd{uid})"/>')
                b.append(_t(cell_cx, cell_y+isz/2+16, f"{idx+1:02d}", isz*0.32, badge_ink,
                            MINCHO, "700", "middle"))
            text_y = cell_y + isz + 44
            b.append(_t(cell_cx, text_y, head, 29, p["accent"] if p["light"] else p["ink"],
                        MINCHO, "600", "middle"))
            if note:
                b.append(_t(cell_cx, text_y+33, note, 22, p["sub"], GOTHIC, anchor="middle"))
        for r in range(rows-1):
            sep_y = top + (r+1)*row_h - 16
            b.append(_hair(p, M, W-M, sep_y, op="0.18", w="0.7"))
    else:
        # アイコンを一切使わない場合は従来通りの横並び（ナンバーバッジ+見出し・補足）
        for idx, it in enumerate(items):
            head, note = it[0], it[1]
            col, row = idx % cols, idx // cols
            cx, cy = M+col*col_w, top+row*row_h
            b.append(f'<circle cx="{cx+30}" cy="{cy+30}" r="26" fill="url(#gd{uid})"/>')
            b.append(_t(cx+30, cy+39, f"{idx+1:02d}", 23, badge_ink, MINCHO, "700", "middle"))
            tx = cx + 74
            b.append(_t(tx, cy+22, head, 27, p["accent"] if p["light"] else p["ink"], MINCHO, "600"))
            if note:
                b.append(_t(tx, cy+56, note, 21, p["sub"], GOTHIC))
    if closing:
        b.append(_hair(p, M, W-M, bottom+10, op="0.3"))
        b.append(_t(M, bottom+52, closing, 30, p["accent"], MINCHO, "600"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def flow_slide(wine_type, eyebrow, title, steps, num=None, total=9, grape=None, closing=None):
    """矢印つきの縦型工程フロー。steps=[str, ...] または
    steps=[str または [str, icon], ...]（icon=data URI、任意。各1行想定）。
    iconがある場合はアイコンが主役級サイズ（目安80〜110px）になるようボックス高さも拡大する。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    has_any_icon = any(isinstance(raw, (list, tuple)) and len(raw) > 1 and raw[1] for raw in steps)
    n=len(steps); y=470; span=780
    step=min(170 if has_any_icon else 150, span//max(n,1))
    bh = min(130, step-24) if has_any_icon else 64
    isz = max(80, min(110, bh-24))
    for i, raw in enumerate(steps):
        if isinstance(raw, (list, tuple)):
            s, icon = raw[0], (raw[1] if len(raw) > 1 else None)
        else:
            s, icon = raw, None
        b.append(f'<rect x="{M}" y="{y}" width="{W-2*M}" height="{bh}" rx="12" fill="none" '
                 f'stroke="{p["frame"]}" stroke-width="1.2" stroke-opacity="0.6"/>')
        if icon:
            b.append(_img(M+14, y+(bh-isz)/2, isz, isz, icon, uid, f"fl{i}", rx=12))
            tx = M + 14 + isz + 22
        else:
            tx = M + 28
        b.append(_t(tx, y+bh/2+9, s, 29, p["ink"], MINCHO, "600"))
        b.append(_t(W-M-24, y+bh/2+8, f"{i+1:02d}", 22, p["gold"], GOTHIC, "600", anchor="end"))
        if i < n-1:
            b.append(_t(W/2, y+bh+(step-bh)/2+8, "▼", 22, p["gold"], GOTHIC, "400", "middle"))
        y += step
    if closing:
        b.append(_hair(p, M, W-M, y+6, op="0.3"))
        b.append(_t(M, y+56, closing, 30, p["accent"], MINCHO, "600"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def ranking_slide(wine_type, eyebrow, title, items, num=None, total=9, grape=None, closing=None):
    """番号付きランキングリスト。items=[(rank, head, note), ...] または
    items=[(rank, head, note, icon), ...]（rankは"1"等の文字列、icon=data URI・任意）"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    n=len(items)
    has_any_icon = any(len(it) >= 4 and it[3] for it in items)
    if has_any_icon:
        y=460; step=min(230, 800//max(n,1)); isz=112
        for idx, it in enumerate(items):
            rank, head, note = it[0], it[1], it[2]
            icon = it[3] if len(it) >= 4 else None
            if icon:
                b.append(_img(M, y, isz, isz, icon, uid, f"rk{idx}", rx=14))
                b.append(f'<rect x="{M}" y="{y}" width="{isz}" height="{isz}" rx="14" '
                         f'fill="none" stroke="{p["frame"]}" stroke-width="1.2" stroke-opacity="0.55"/>')
                tx = M + isz + 24
            else:
                tx = M
            b.append(f'<circle cx="{M+24}" cy="{y-4}" r="21" fill="url(#gd{uid})"/>')
            b.append(_t(M+24, y+4, str(rank), 21, INK_LIGHT, MINCHO, "700", "middle"))
            ty = y + isz/2 - 16
            b.append(_t(tx, ty, head, 30, p["accent"] if p["light"] else p["ink"], MINCHO, "600"))
            if note:
                b.append(_t(tx, ty+34, note, 21, p["sub"], GOTHIC))
            b.append(_hair(p, M, W-M, y+isz+24, op="0.16", w="0.7"))
            y += step
    else:
        y=470; step=min(140, 760//max(n,1))
        for idx, it in enumerate(items):
            rank, head, note = it[0], it[1], it[2]
            b.append(_t(M+6, y, str(rank), 40, p["gold"], MINCHO, "700"))
            tx = M + 90
            b.append(_t(tx, y, head, 32, p["accent"] if p["light"] else p["ink"], MINCHO, "600"))
            if note:
                b.append(_t(tx, y+34, note, 22, p["sub"], GOTHIC))
            b.append(_hair(p, M, W-M, y+50, op="0.16", w="0.7"))
            y += step
    if closing:
        b.append(_t(M, y+40, closing, 30, p["accent"], MINCHO, "600"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def compare_slide(wine_type, eyebrow, title, left, right, num=None, total=9, grape=None,
                  closing=None):
    """二択比較ボックス（北vs南、伝統的vs現代的など対比構造向け）。
    left / right = {"label":.., "sublabel":.. (任意), "body":[str,...]（1〜4行想定）,
                    "tag":.. (任意・下部の縁取りピル), "photo": data URI（任意）}。
    左右で縁取りピルの色を変え（gold/accent）視覚的に対比を強調する。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    top = 380; gap = 48
    col_w = (W - 2*M - gap) // 2
    bottom = H - 200
    b.append(f'<line x1="{W/2}" y1="{top}" x2="{W/2}" y2="{bottom}" stroke="{p["gold"]}" '
             f'stroke-opacity="0.25" stroke-width="1"/>')
    tag_colors = [p["gold"], p["accent"]]
    for i, side in enumerate([left, right]):
        x = M if i == 0 else M + col_w + gap
        y = top
        if side.get("photo"):
            ph = 200
            b.append(_img(x, y, col_w, ph, side["photo"], uid, f"cmp{i}", rx=8))
            b.append(f'<rect x="{x}" y="{y}" width="{col_w}" height="{ph}" rx="8" fill="none" '
                     f'stroke="{p["frame"]}" stroke-width="1" stroke-opacity="0.5"/>')
            y += ph + 30
        b.append(_t(x, y, side["label"], 32, p["accent"] if p["light"] else p["ink"], MINCHO, "700"))
        y += 34
        if side.get("sublabel"):
            b.append(_t(x, y, side["sublabel"], 20, p["sub"], GOTHIC, "500"))
            y += 30
        y += 14
        b.append(_hair(p, x, x+col_w, y, op="0.3"))
        y += 34
        for line in side.get("body", [])[:4]:
            b.append(_t(x, y, line, 23, p["ink"], GOTHIC))
            y += 32
        if side.get("tag"):
            tagtext = side["tag"]
            tw = min(col_w, max(90, len(tagtext)*24+40))
            tag_y = bottom - 60
            col = tag_colors[i]
            b.append(f'<rect x="{x}" y="{tag_y}" width="{tw}" height="44" rx="22" fill="none" '
                     f'stroke="{col}" stroke-width="1.4"/>')
            b.append(_t(x+tw/2, tag_y+29, tagtext, 20, col, GOTHIC, "600", "middle", spacing="1"))
    if closing:
        b.append(_hair(p, M, W-M, bottom+10, op="0.3"))
        b.append(_t(M, bottom+52, closing, 30, p["accent"], MINCHO, "600"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def sequence_slide(wine_type, eyebrow, title, nodes, headline=None, num=None, total=9,
                   grape=None, closing=None):
    """アイコン＋矢印の横並び工程チェーン（樽→瓶熟成のようなタイムライン向け）。
    nodes=[{"icon": data URI（任意）, "label": str（\\nで2行まで）}, ...]（2〜6個想定）。
    headline=チェーン上部に大きく出す数値・要約（例："最低熟成期間 3年2ヶ月"、任意）。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    top = 380
    if headline:
        b.append(_t(W/2, top+50, headline, 44, p["accent"], MINCHO, "700", "middle", spacing="1"))
        row_y = top + 130
    else:
        row_y = top + 60
    n = len(nodes); arrow_w = 44
    avail = W - 2*M - (n-1)*arrow_w
    isz = max(70, min(140, avail // n - 20))
    cell_w = avail // n
    x = M
    for i, node in enumerate(nodes):
        icon = node.get("icon"); label = node.get("label", "")
        cx = x + cell_w/2
        cy = row_y + isz/2
        if icon:
            icon_x = cx - isz/2
            b.append(_img(icon_x, row_y, isz, isz, icon, uid, f"sq{i}", rx=14))
            b.append(f'<rect x="{icon_x}" y="{row_y}" width="{isz}" height="{isz}" rx="14" '
                     f'fill="none" stroke="{p["frame"]}" stroke-width="1.2" stroke-opacity="0.55"/>')
        else:
            b.append(f'<circle cx="{cx}" cy="{cy}" r="{isz/2}" fill="url(#gd{uid})"/>')
            b.append(_t(cx, cy+isz*0.12, f"{i+1:02d}", isz*0.32, INK_LIGHT, MINCHO, "700", "middle"))
        lines = label.split("\n")
        ly = row_y + isz + 36
        for li, line in enumerate(lines[:2]):
            b.append(_t(cx, ly+li*26, line, 22, p["ink"], GOTHIC, "600", "middle"))
        if i < n-1:
            ax = x + cell_w + arrow_w/2
            b.append(_t(ax, cy+8, "→", 30, p["gold"], GOTHIC, "400", "middle"))
        x += cell_w + arrow_w
    bottom_y = row_y + isz + 36 + 26*2 + 24
    if closing:
        b.append(_hair(p, M, W-M, bottom_y, op="0.3"))
        b.append(_t(M, bottom_y+50, closing, 30, p["accent"], MINCHO, "600"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def _scroll_flourish(cx, y, w, color, flip=False):
    """タイトル上下の簡易装飾罫線（唐草風の小さな弧＋центральひし形）。"""
    hw = w/2
    yy = H-y if flip else y
    return (f'<path d="M{cx-hw},{yy} Q{cx-hw*0.5},{yy-14} {cx},{yy} '
            f'Q{cx+hw*0.5},{yy-14} {cx+hw},{yy}" fill="none" stroke="{color}" '
            f'stroke-width="1.2" stroke-opacity="0.55"/>'
            f'<rect x="{cx-6}" y="{yy-6}" width="12" height="12" fill="{color}" '
            f'fill-opacity="0.7" transform="rotate(45 {cx} {yy})"/>')

def myth_slide(wine_type, title_main, title_neg, title_pos, center_photo, boxes,
               closing=None, num=None, total=9, grape=None):
    """中央に大きな縦長ヒーロー写真、その左右に番号付きボックスを2段×2列で配置する
    「誤解を解く」型インフォグラフィック（タンニン／酸味のようなテーマ解説向け）。
    title_main・title_neg・title_pos → 見出しは f"{title_main}——『{title_neg}』ではなく、{title_pos}"。
    center_photo = data URI（任意・縦長トリミング推奨）。
    boxes = 4個の {"num":1-4, "heading":str,
                   "layout":"vs"（2項目を左右比較） または "list"（1〜4項目を縦積み）,
                   "items":[{"label":str,"note":str（任意・\\nで複数行）,"icon":data URI（任意）}, ...]}。
    closing = 最下部の1行まとめ（任意）。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; cx=W/2; b=[]
    b.append(_scroll_flourish(cx, 56, 420, p["gold"]))
    title = f"{title_main}——『{title_neg}』ではなく、{title_pos}"
    if len(title) <= 16: tsz = 46
    elif len(title) <= 22: tsz = 38
    elif len(title) <= 28: tsz = 32
    else: tsz = 26
    b.append(_t(cx, 118, title, tsz, p["ink"], MINCHO, "700", "middle", spacing="0.5"))
    b.append(_hair(p, cx-260, cx+260, 150, op="0.5"))

    top, bottom = 210, H-150
    total_h = bottom - top; row_gap = 36
    row_h = (total_h - row_gap) / 2
    left_w, center_w, right_w, col_gap = 310, 220, 310, 24
    left_x = M; center_x = left_x + left_w + col_gap; right_x = center_x + center_w + col_gap

    b.append(_img(center_x, top, center_w, total_h, center_photo, uid, "hero", rx=14))
    b.append(f'<rect x="{center_x}" y="{top}" width="{center_w}" height="{total_h}" rx="14" '
             f'fill="none" stroke="{p["frame"]}" stroke-width="1.2" stroke-opacity="0.6"/>')

    positions = [(left_x, top), (right_x, top), (left_x, top+row_h+row_gap), (right_x, top+row_h+row_gap)]
    box_w = left_w
    for box, (bx, by) in zip(boxes, positions):
        heading = f'{box["num"]}｜{box["heading"]}'
        pw = min(box_w, len(heading)*20+40)
        b.append(f'<rect x="{bx}" y="{by}" width="{pw}" height="38" rx="8" fill="none" '
                 f'stroke="{p["accent"]}" stroke-width="1.3"/>')
        b.append(_t(bx+pw/2, by+25, heading, 19, p["accent"], GOTHIC, "700", "middle", spacing="1"))
        b.append(f'<rect x="{bx}" y="{by+52}" width="{box_w}" height="{row_h-52}" rx="8" '
                 f'fill="none" stroke="{p["frame"]}" stroke-width="1" stroke-opacity="0.4"/>')
        cy0 = by + 52
        items = box.get("items", [])
        layout = box.get("layout", "list")
        if layout == "vs" and len(items) >= 2:
            inner_h = row_h - 52
            half_h = inner_h/2
            icx = bx + box_w/2
            for j, it in enumerate(items[:2]):
                iy0 = cy0 + j*half_h
                icon = it.get("icon")
                label = it["label"]
                if len(label) > 12:
                    mid = (len(label)+1)//2
                    label_lines = [label[:mid], label[mid:]]
                else:
                    label_lines = [label]
                note_lines = it.get("note", "").split("\n") if it.get("note") else []
                isz = 52
                content_h = (isz+26 if icon else 22) + len(label_lines)*22 + \
                            (24+len(note_lines[:2])*19 if note_lines else 0)
                start_y = iy0 + max(6, (half_h-content_h)/2)
                if icon:
                    b.append(_img(icx-isz/2, start_y, isz, isz, icon, uid, f"my{box['num']}_{j}", rx=10))
                    ly = start_y + isz + 26
                else:
                    ly = start_y + 22
                for k, line in enumerate(label_lines):
                    b.append(_t(icx, ly+k*22, line, 20, p["ink"], MINCHO, "600", "middle"))
                note_y = ly + (len(label_lines)-1)*22 + 24
                for k, line in enumerate(note_lines[:2]):
                    b.append(_t(icx, note_y+k*19, line, 15, p["sub"], GOTHIC, anchor="middle"))
            mid_y = cy0 + half_h
            b.append(f'<line x1="{bx+10}" y1="{mid_y}" x2="{icx-18}" y2="{mid_y}" '
                     f'stroke="{p["gold"]}" stroke-opacity="0.4" stroke-width="1"/>')
            b.append(f'<line x1="{icx+18}" y1="{mid_y}" x2="{bx+box_w-10}" y2="{mid_y}" '
                     f'stroke="{p["gold"]}" stroke-opacity="0.4" stroke-width="1"/>')
            b.append(f'<circle cx="{icx}" cy="{mid_y}" r="16" fill="url(#gd{uid})"/>')
            b.append(_t(icx, mid_y+5, "VS", 14, INK_LIGHT, GOTHIC, "700", "middle"))
        elif layout == "list" and len(items) == 1:
            it = items[0]; icon = it.get("icon"); icx = bx+box_w/2
            label = it.get("label", "")
            note_lines = it.get("note", "").split("\n")[:2] if it.get("note") else []
            isz = 90
            avail_h = row_h - 52
            content_h = (isz+30 if icon else 0) + (24 if label else 0) + len(note_lines)*20
            start_y = cy0 + max(8, (avail_h-content_h)/2)
            if icon:
                b.append(_img(icx-isz/2, start_y, isz, isz, icon, uid, f"my{box['num']}_0", rx=14))
                ly = start_y + isz + 30
            else:
                ly = start_y + 20
            if label:
                b.append(_t(icx, ly, label, 17, p["ink"], MINCHO, "700", "middle"))
                ly += 24
            for k, line in enumerate(note_lines):
                b.append(_t(icx, ly+k*20, line, 15, p["sub"], GOTHIC, anchor="middle"))
        else:
            n = len(items); irow = (row_h-52)/max(n,1)
            icx = bx + box_w/2
            for j, it in enumerate(items):
                row_y0 = cy0 + j*irow
                icon = it.get("icon")
                isz = min(44, irow-44)
                block_h = isz + 10 + 24
                start_y = row_y0 + max(4, (irow-block_h)/2)
                b.append(_img(icx-isz/2, start_y, isz, isz, icon, uid, f"my{box['num']}_{j}", rx=8))
                ly = start_y + isz + 22
                b.append(_t(icx, ly, it["label"], 20, p["ink"], MINCHO, "600", "middle"))

    if closing:
        b.append(_hair(p, cx-320, cx+320, bottom+34, op="0.4"))
        b.append(_t(cx, bottom+68, closing, 22, p["accent"], MINCHO, "600", "middle"))
    b.append(_scroll_flourish(cx, H-40, 360, p["gold"], flip=False))
    return _svg(p, uid, "".join(b))

def region_map_slide(wine_type, eyebrow, title, map_photo, pins, closing=None,
                     num=None, total=9, grape=None, map_aspect=1.0, legend_cols=4):
    """地図写真（上段・番号ドットのみ）＋ 地域一覧の凡例グリッド（下段・番号＋写真＋ラベル）
    という2段構成のヒーロー画像（ワインペアリングシリーズの導入・表紙向け）。
    番号が多い（10件超）場合に地図上へ直接写真を乗せると密集地帯で重なるため、
    地図には位置確認用の小さな番号ドットだけを置き、詳細は下の凡例へ分離する。
    map_photo = 地図写真のdata URI。
    map_aspect = 地図画像の 幅/高さ（例: 正方形なら1.0）。枠内に全体が収まるよう
    contain-fit で配置し、はみ出し・トリミングを防ぐ。pinの座標はこの実表示領域基準。
    pins = [{"label":str, "x":0.0-1.0, "y":0.0-1.0（地図画像内の相対位置、左上原点）,
             "photo": data URI（任意）}, ...]。
    legend_cols = 凡例グリッドの列数（既定4）。"""
    p=_prep(wine_type, grape); uid=p["_uid"]
    b=_header(p, eyebrow, title, y_eb=140, y_ti=230, y_hr=280)
    box_x, box_y = M, 310
    box_w, box_h = W - 2*M, 330
    # contain-fit：枠内に地図全体が収まるよう実表示矩形を計算
    if box_w / box_h > map_aspect:
        map_h = box_h; map_w = map_h * map_aspect
    else:
        map_w = box_w; map_h = map_w / map_aspect
    map_x = box_x + (box_w - map_w) / 2
    map_y = box_y + (box_h - map_h) / 2
    cid_map = f"clipmapbox{uid}"
    b.append(f'<clipPath id="{cid_map}"><rect x="{map_x}" y="{map_y}" width="{map_w}" height="{map_h}"/></clipPath>')
    b.append(f'<image x="{map_x}" y="{map_y}" width="{map_w}" height="{map_h}" '
             f'href="{map_photo}" xlink:href="{map_photo}" preserveAspectRatio="xMidYMid meet" '
             f'clip-path="url(#{cid_map})"/>')

    n = len(pins)
    for idx, pin in enumerate(pins):
        px = map_x + max(0.0, min(1.0, pin["x"])) * map_w
        py = map_y + max(0.0, min(1.0, pin["y"])) * map_h
        b.append(f'<circle cx="{px}" cy="{py}" r="11" fill="url(#gd{uid})" '
                 f'stroke="{p["bg1"]}" stroke-width="1.5"/>')
        b.append(_t(px, py+4, str(idx+1), 12, INK_LIGHT, GOTHIC, "700", "middle"))

    # 凡例グリッド（番号・写真サムネイル（大）・州名＋料理名）
    legend_top = box_y + box_h + 30
    legend_bottom = H - (150 if closing else 110)
    cols = max(1, legend_cols)
    rows = (n + cols - 1) // cols
    cell_w = box_w / cols
    cell_h = (legend_bottom - legend_top) / max(rows, 1)
    isz = min(cell_h - 16, cell_w * 0.42, 96)
    for idx, pin in enumerate(pins):
        col, row = idx % cols, idx // cols
        cx0 = box_x + col*cell_w
        cy0 = legend_top + row*cell_h
        icx, icy = cx0 + isz/2 + 4, cy0 + cell_h/2
        photo = pin.get("photo")
        if photo:
            cid = f"legmap{uid}_{idx}"
            b.append(f'<clipPath id="{cid}"><circle cx="{icx}" cy="{icy}" r="{isz/2}"/></clipPath>')
            b.append(f'<image x="{icx-isz/2}" y="{icy-isz/2}" width="{isz}" height="{isz}" '
                     f'href="{photo}" xlink:href="{photo}" preserveAspectRatio="xMidYMid slice" '
                     f'clip-path="url(#{cid})"/>')
            b.append(f'<circle cx="{icx}" cy="{icy}" r="{isz/2}" fill="none" '
                     f'stroke="{p["gold"]}" stroke-width="1.4"/>')
        else:
            b.append(f'<circle cx="{icx}" cy="{icy}" r="{isz/2}" fill="#808080" fill-opacity="0.15" '
                     f'stroke="#808080" stroke-opacity="0.4" stroke-width="1.2" stroke-dasharray="3,3"/>')
        badge_r = 12
        b.append(f'<circle cx="{cx0+isz-2}" cy="{cy0+cell_h/2-isz/2+2}" r="{badge_r}" fill="url(#gd{uid})" '
                 f'stroke="{p["bg1"]}" stroke-width="1.5"/>')
        b.append(_t(cx0+isz-2, cy0+cell_h/2-isz/2+6, str(idx+1), 13, INK_LIGHT, GOTHIC, "700", "middle"))
        tx = cx0 + isz + 18
        avail_chars = max(4, (cell_w - isz - 22) / 9.5)
        label = pin["label"]
        dish = pin.get("dish", "")
        if dish:
            lsz = 17 if len(label) <= avail_chars*0.62 else (15 if len(label) <= avail_chars*0.78 else 13)
            b.append(_t(tx, icy-6, label, lsz, p["ink"], GOTHIC, "700"))
            dsz = 13 if len(dish) <= avail_chars*0.75 else (11 if len(dish) <= avail_chars else 9.5)
            b.append(_t(tx, icy+15, dish, dsz, p["sub"], GOTHIC, "500"))
        else:
            lsz = 17 if len(label) <= avail_chars*0.62 else (15 if len(label) <= avail_chars*0.78 else 13)
            b.append(_t(tx, icy+5, label, lsz, p["ink"], GOTHIC, "600"))

    if closing:
        b.append(_hair(p, M, W-M, legend_bottom+18, op="0.3"))
        b.append(_t(W/2, legend_bottom+48, closing, 22, p["accent"], MINCHO, "600", "middle"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def quadrant_slide(wine_type, eyebrow, title, x_axis, y_axis, points, num=None, total=9, grape=None):
    """2軸4象限マトリクス。x_axis=(左ラベル,右ラベル) y_axis=(下ラベル,上ラベル)
    points=[(label, x, y), ...]  x,y は 0.0〜1.0（左下原点）"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=_header(p, eyebrow, title)
    px0, py0, pw, ph = M+40, 480, W-2*M-80, 600
    cx, cy = px0+pw/2, py0+ph/2
    b.append(f'<line x1="{px0}" y1="{cy}" x2="{px0+pw}" y2="{cy}" stroke="{p["gold"]}" '
             f'stroke-opacity="0.45" stroke-width="1.2"/>')
    b.append(f'<line x1="{cx}" y1="{py0}" x2="{cx}" y2="{py0+ph}" stroke="{p["gold"]}" '
             f'stroke-opacity="0.45" stroke-width="1.2"/>')
    b.append(_t(px0, cy-14, x_axis[0], 22, p["sub"], GOTHIC, "500"))
    b.append(_t(px0+pw, cy-14, x_axis[1], 22, p["sub"], GOTHIC, "500", anchor="end"))
    b.append(_t(cx, py0-16, y_axis[1], 22, p["sub"], GOTHIC, "500", "middle"))
    b.append(_t(cx, py0+ph+34, y_axis[0], 22, p["sub"], GOTHIC, "500", "middle"))
    for label, x, y in points:
        px = px0 + max(0.0, min(1.0, x))*pw
        pyv = py0 + ph - max(0.0, min(1.0, y))*ph
        b.append(f'<circle cx="{px}" cy="{pyv}" r="9" fill="url(#gd{uid})"/>')
        b.append(_t(px, pyv-18, label, 24, p["ink"], MINCHO, "600", "middle"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

# ===================== 診断（クイズ）用 =====================
def _marker(p, cx, cy, kind, r=36):
    """選択肢マーカー。kind=circle/triangle/square/diamond は図形、
    それ以外の文字列（"A" "Lv.2" など）は丸囲みの文字として描く。"""
    k=r/36.0; a=p["accent"]
    b=[f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{p["gold"]}" stroke-width="1.6"/>']
    if kind=="circle":
        b.append(f'<circle cx="{cx}" cy="{cy}" r="{14*k:.1f}" fill="{a}"/>')
    elif kind=="triangle":
        pts=f"{cx},{cy-17*k:.1f} {cx+16*k:.1f},{cy+12*k:.1f} {cx-16*k:.1f},{cy+12*k:.1f}"
        b.append(f'<polygon points="{pts}" fill="{a}"/>')
    elif kind=="square":
        b.append(f'<rect x="{cx-13*k:.1f}" y="{cy-13*k:.1f}" width="{26*k:.1f}" height="{26*k:.1f}" fill="{a}"/>')
    elif kind=="diamond":
        pts=f"{cx},{cy-18*k:.1f} {cx+18*k:.1f},{cy} {cx},{cy+18*k:.1f} {cx-18*k:.1f},{cy}"
        b.append(f'<polygon points="{pts}" fill="{a}"/>')
    else:
        size=(34 if len(kind)<=1 else 22)*k
        b.append(_t(cx, cy+size*0.36, kind, size, a, MINCHO, "700", "middle"))
    return "".join(b)

def quiz_slide(wine_type, eyebrow, question, options, note=None, num=None, total=9, grape=None):
    """診断の設問（または集計）スライド。question=1行の文字列 or 行のリスト（最大2行）。
    options=[(marker, head) または (marker, head, sub), ...]（3〜4個）。
    marker は _marker 参照。note=カード下の補足1行（任意）。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; b=[_eyebrow(p, M, 200, eyebrow)]
    lines=[question] if isinstance(question,str) else list(question)
    y=292
    for ln in lines:
        b.append(_t(M, y, ln, 52, p["ink"], MINCHO, "700", spacing="2")); y+=70
    hr_y=y-28
    b.append(_hair(p, M, W-M, hr_y, op="0.45", w="1.2"))
    n=len(options); gap=22; top=hr_y+50
    bottom=H-150-(64 if note else 0)
    ch=min(170, (bottom-top-(n-1)*gap)/n)
    fill, fop = ("#FFFFFF","0.55") if p["light"] else ("#FFFFFF","0.06")
    for i, opt in enumerate(options):
        mk, head = opt[0], opt[1]
        sub = opt[2] if len(opt)>=3 else None
        cy0=top+i*(ch+gap); mid=cy0+ch/2
        b.append(f'<rect x="{M}" y="{cy0:.1f}" width="{W-2*M}" height="{ch:.1f}" rx="18" '
                 f'fill="{fill}" fill-opacity="{fop}" stroke="{p["frame"]}" '
                 f'stroke-opacity="0.55" stroke-width="1.4"/>')
        b.append(_marker(p, M+66, round(mid,1), mk))
        tx=M+130
        if sub:
            b.append(_t(tx, mid-2, head, 34, p["accent"] if p["light"] else p["ink"], MINCHO, "600"))
            b.append(_t(tx, mid+40, sub, 25, p["sub"], GOTHIC))
        else:
            b.append(_t(tx, mid+12, head, 34, p["ink"], MINCHO, "600"))
    if note:
        b.append(_t(W/2, bottom+44, note, 24, p["sub"], GOTHIC, anchor="middle", spacing="1"))
    b.append(_footer(p, num, total))
    return _svg(p, uid, "".join(b))

def result_slide(wine_type, eyebrow, marker, name, lines, step, cta=None,
                 step_label="次の一歩", grape=None):
    """診断の結果スライド（暗地=classic推奨）。marker=図形名 or 短い文字、name=結果名、
    lines=説明（2〜4行）、step=次の一歩（1〜3行）、cta=最下部の一言。"""
    p=_prep(wine_type, grape); uid=p["_uid"]; cx=W/2; b=[]
    b.append(_eyebrow(p, cx, 190, eyebrow, "middle"))
    b.append(_marker(p, cx, 322, marker, r=62))
    nsz=72 if len(name)<=9 else 58
    b.append(_t(cx, 478, name, nsz, p["accent"], MINCHO, "700", "middle", spacing="2"))
    b.append(_hair(p, cx-190, cx+190, 528, op="0.5"))
    y=600
    for ln in lines:
        b.append(_t(cx, y, ln, 33, p["ink"], GOTHIC, anchor="middle")); y+=52
    box_y=y+28; bh=104+len(step)*54
    b.append(f'<rect x="{M}" y="{box_y}" width="{W-2*M}" height="{bh}" rx="20" '
             f'fill="{p["gold"]}" fill-opacity="0.09" stroke="{p["gold"]}" '
             f'stroke-opacity="0.8" stroke-width="1.4"/>')
    b.append(_t(cx, box_y+52, f"NEXT STEP ・ {step_label}", 22, p["gold"], GOTHIC, "600",
                "middle", spacing="4"))
    sy=box_y+112
    for ln in step:
        b.append(_t(cx, sy, ln, 36, p["ink"], MINCHO, "600", "middle", spacing="1")); sy+=54
    if cta:
        b.append(_t(cx, H-110, cta, 26, p["gold"], GOTHIC, "500", "middle", spacing="3"))
    return _svg(p, uid, "".join(b))

# ===================== 書き出し =====================
def export(slides, outdir, name, png_width=540):
    import cairosvg
    os.makedirs(f"{outdir}/svg", exist_ok=True)
    os.makedirs(f"{outdir}/png", exist_ok=True)
    for i, s in enumerate(slides, 1):
        sp=f"{outdir}/svg/{name}_{i:02d}.svg"
        with open(sp,"w",encoding="utf-8") as f: f.write(s)
        cairosvg.svg2png(url=sp, write_to=f"{outdir}/png/{name}_{i:02d}.png",
                         output_width=png_width, output_height=round(png_width*H/W))
    return len(slides)
