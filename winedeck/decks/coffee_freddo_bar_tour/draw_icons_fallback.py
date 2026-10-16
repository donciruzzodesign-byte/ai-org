#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI画像生成APIのクレジット切れのため代替手段：Pillowでブランドカラーの
フラットイラスト調アイコンを直接ベクター描画する（system cairo不要）。
4倍解像度で描いてダウンサンプルしアンチエイリアスをかける。
将来 OPENAI_API_KEY にクレジットが復活したら fetch_icons.py（AI生成）に置き換え可能
（同じファイル名・同じ出力先のため、置き換えるだけでJSON側の変更は不要）。
"""
import os
import math
from PIL import Image, ImageDraw

OUT_DIR = "/Users/kubotahironori/ai-org/winedeck/decks/coffee_freddo_bar_tour/icons"
S = 1024          # 出力サイズ
SS = 4             # スーパーサンプリング倍率
C = S * SS

WINE = (107, 26, 42, 255)      # #6B1A2A
WINE_SOFT = (107, 26, 42, 140)
GOLD = (201, 168, 76, 255)     # #C9A84C
GOLD_SOFT = (201, 168, 76, 150)
CREAM = (245, 240, 232, 255)   # #F5F0E8
INK = (43, 43, 43, 255)        # #2B2B2B

def canvas():
    return Image.new("RGBA", (C, C), (0, 0, 0, 0))

def save(im, name):
    im = im.resize((S, S), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    im.save(path, "PNG")
    print("wrote", path)

def lw(px):
    return max(1, int(px * SS))

# ---------- icon 1: シチリア グラニータ・ディ・カッフェ + ブリオッシュ ----------
def sicilia_granita():
    im = canvas(); d = ImageDraw.Draw(im)
    # グラス（台形、上広がり）
    gx0, gx1 = 0.34, 0.66
    gy0, gy1 = 0.20, 0.66
    bx0, bx1 = 0.40, 0.60
    pts = [(gx0*C, gy0*C), (gx1*C, gy0*C), (bx1*C, gy1*C), (bx0*C, gy1*C)]
    d.polygon(pts, fill=CREAM, outline=INK, width=lw(6))
    # グラニータ層（横ライン、ワインレッド〜ゴールド）
    for i, frac in enumerate([0.30, 0.46, 0.60]):
        y = (gy0 + (gy1-gy0)*frac) * C
        xL = (gx0 + (bx0-gx0)*frac) * C
        xR = (gx1 - (gx1-bx1)*frac) * C
        col = WINE if i % 2 == 0 else GOLD
        d.line([(xL, y), (xR, y)], fill=col, width=lw(10))
    d.rectangle([bx0*C, (gy0+(gy1-gy0)*0.62)*C, bx1*C, gy1*C], fill=WINE_SOFT)
    # スプーン
    d.line([(0.60*C, 0.18*C), (0.50*C, 0.40*C)], fill=GOLD, width=lw(6))
    d.ellipse([0.575*C, 0.150*C, 0.625*C, 0.190*C], fill=GOLD, outline=INK, width=lw(3))
    # ブリオッシュ（col tuppo：大きい玉+小さい玉）
    bcx, bcy, br = 0.76, 0.62, 0.11
    d.ellipse([(bcx-br)*C, (bcy-br)*C, (bcx+br)*C, (bcy+br)*C], fill=GOLD, outline=INK, width=lw(6))
    tr = 0.045
    d.ellipse([(bcx-tr)*C, (bcy-br-tr*1.5)*C, (bcx+tr)*C, (bcy-br+tr*0.5)*C], fill=GOLD, outline=INK, width=lw(5))
    save(im, "sicilia_granita.png")

# ---------- icon 2: レッチェ カフェ・レッチェーゼ ----------
def lecce_caffe():
    im = canvas(); d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = 0.32, 0.68, 0.24, 0.72
    d.rounded_rectangle([x0*C, y0*C, x1*C, y1*C], radius=int(0.03*C), fill=CREAM, outline=INK, width=lw(6))
    # アーモンドミルク（下側・クリーム系）とエスプレッソ（上側・層になって注がれる、ワインレッド）
    midy = y0 + (y1-y0)*0.42
    d.rectangle([x0*C+lw(3), y0*C+lw(3), x1*C-lw(3), midy*C], fill=WINE)
    # 中間のグラデーション帯（marbled pour effect）
    d.line([(x0*C, midy*C), (x1*C, midy*C)], fill=GOLD, width=lw(8))
    # ストロー
    d.line([(0.58*C, 0.10*C), (0.44*C, 0.30*C)], fill=GOLD, width=lw(9))
    save(im, "lecce_caffe.png")

# ---------- icon 3: トリノ ビチェリン（3層） ----------
def torino_bicerin():
    im = canvas(); d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = 0.30, 0.70, 0.30, 0.74
    d.rounded_rectangle([x0*C, y0*C, x1*C, y1*C], radius=int(0.04*C), fill=CREAM, outline=INK, width=lw(6))
    h = y1 - y0
    # 下段：コーヒー（ワインレッド）
    d.rectangle([x0*C+lw(3), (y0+h*0.62)*C, x1*C-lw(3), y1*C-lw(3)], fill=WINE)
    # 中段：チョコレート（ゴールド濃いめ）
    d.rectangle([x0*C+lw(3), (y0+h*0.30)*C, x1*C-lw(3), (y0+h*0.62)*C], fill=GOLD)
    # 上段：ホイップクリーム（クリーム色、渦ライン）
    d.rectangle([x0*C+lw(3), y0*C+lw(3), x1*C-lw(3), (y0+h*0.30)*C], fill=CREAM)
    for i in range(3):
        cx = (x0 + (x1-x0)*(0.28+0.24*i)) * C
        cy = (y0 + h*0.15) * C
        d.arc([cx-0.05*C, cy-0.05*C, cx+0.05*C, cy+0.05*C], start=0, end=280, fill=INK, width=lw(4))
    save(im, "torino_bicerin.png")

# ---------- icon 4: 温度と香りの関係 ----------
def temperatura_aroma():
    im = canvas(); d = ImageDraw.Draw(im)
    # 温度計（縦棒+球）
    tx, ty0, ty1 = 0.34, 0.16, 0.66
    w = 0.05
    d.rounded_rectangle([(tx-w)*C, ty0*C, (tx+w)*C, ty1*C], radius=int(w*C), fill=CREAM, outline=INK, width=lw(6))
    d.line([(tx*C, (ty0+0.05)*C), (tx*C, (ty1-0.05)*C)], fill=WINE, width=lw(int(w*C*0.9)))
    br = 0.10
    d.ellipse([(tx-br)*C, (ty1-br)*C, (tx+br)*C, (ty1+br)*C], fill=WINE, outline=INK, width=lw(6))
    for i in range(3):
        yy = (ty0 + 0.10 + i*0.10) * C
        d.line([((tx+w)*C, yy), ((tx+w+0.05)*C, yy)], fill=INK, width=lw(4))
    # 開いた香り（緩やかな渦）右上
    ocx, ocy = 0.66, 0.30
    d.arc([(ocx-0.14)*C, (ocy-0.14)*C, (ocx+0.14)*C, (ocy+0.14)*C], start=200, end=520, fill=GOLD, width=lw(9))
    d.arc([(ocx-0.07)*C, (ocy-0.20)*C, (ocx+0.21)*C, (ocy+0.08)*C], start=200, end=460, fill=GOLD, width=lw(9))
    # 閉じた香り（小さくタイトな渦）右下
    ccx, ccy = 0.68, 0.62
    for r in (0.10, 0.06, 0.03):
        d.arc([(ccx-r)*C, (ccy-r)*C, (ccx+r)*C, (ccy+r)*C], start=0, end=340, fill=WINE, width=lw(7))
    save(im, "temperatura_aroma.png")

# ---------- icon 5: Shakerato step1 エスプレッソ抽出 ----------
def shakerato_step1_espresso():
    im = canvas(); d = ImageDraw.Draw(im)
    # ポルタフィルター（半円ハンドル+スパウト）
    hx, hy, hr = 0.50, 0.28, 0.14
    d.arc([(hx-hr)*C, (hy-hr)*C, (hx+hr)*C, (hy+hr)*C], start=200, end=340, fill=INK, width=lw(9))
    d.rectangle([(hx-0.16)*C, hy*C, (hx+0.16)*C, (hy+0.06)*C], fill=WINE, outline=INK, width=lw(6))
    # スパウト2本
    d.line([((hx-0.06)*C, (hy+0.06)*C), ((hx-0.09)*C, (hy+0.16)*C)], fill=INK, width=lw(6))
    d.line([((hx+0.06)*C, (hy+0.06)*C), ((hx+0.09)*C, (hy+0.16)*C)], fill=INK, width=lw(6))
    # 抽出液
    d.line([((hx-0.09)*C, (hy+0.16)*C), ((hx-0.06)*C, (hy+0.34)*C)], fill=WINE, width=lw(5))
    d.line([((hx+0.09)*C, (hy+0.16)*C), ((hx+0.06)*C, (hy+0.34)*C)], fill=WINE, width=lw(5))
    # カップ&ソーサー
    cx0, cx1, cy0, cy1 = 0.36, 0.64, 0.62, 0.76
    d.rounded_rectangle([cx0*C, cy0*C, cx1*C, cy1*C], radius=int(0.02*C), fill=CREAM, outline=INK, width=lw(6))
    d.rectangle([cx0*C+lw(3), cy0*C+lw(3), cx1*C-lw(3), (cy0+0.05)*C], fill=WINE)
    d.arc([(cx1-0.02)*C, (cy0+0.02)*C, (cx1+0.09)*C, (cy0+0.10)*C], start=280, end=90, fill=INK, width=lw(6))
    d.ellipse([0.28*C, 0.78*C, 0.72*C, 0.83*C], fill=CREAM, outline=INK, width=lw(6))
    save(im, "shakerato_step1_espresso.png")

# ---------- icon 6: Shakerato step2 氷+砂糖 ----------
def shakerato_step2_shaker():
    im = canvas(); d = ImageDraw.Draw(im)
    # シェイカー本体
    sx0, sx1, sy0, sy1 = 0.36, 0.64, 0.26, 0.70
    d.polygon([(sx0*C, (sy0+0.10)*C), (sx1*C, (sy0+0.10)*C), ((sx1-0.04)*C, sy1*C), ((sx0+0.04)*C, sy1*C)],
              fill=CREAM, outline=INK, width=lw(6))
    # キャップ
    d.rectangle([(sx0+0.02)*C, sy0*C, (sx1-0.02)*C, (sy0+0.10)*C], fill=WINE, outline=INK, width=lw(6))
    d.rectangle([(sx0+0.08)*C, (sy0-0.05)*C, (sx1-0.08)*C, sy0*C], fill=WINE, outline=INK, width=lw(5))
    # 氷キューブ
    for ix, iy in [(0.16, 0.60), (0.20, 0.72), (0.80, 0.58), (0.78, 0.70)]:
        s = 0.07
        d.rounded_rectangle([(ix-s/2)*C, (iy-s/2)*C, (ix+s/2)*C, (iy+s/2)*C],
                             radius=int(0.01*C), fill=GOLD_SOFT, outline=INK, width=lw(4))
    # 砂糖スプーン
    d.line([(0.72*C, 0.22*C), (0.60*C, 0.40*C)], fill=GOLD, width=lw(6))
    d.ellipse([0.685*C, 0.185*C, 0.755*C, 0.235*C], fill=GOLD, outline=INK, width=lw(4))
    save(im, "shakerato_step2_shaker.png")

# ---------- icon 7: Shakerato step3 シェイクする ----------
def shakerato_step3_shake():
    im = canvas(); d = ImageDraw.Draw(im)
    sx0, sx1, sy0, sy1 = 0.38, 0.62, 0.30, 0.72
    d.polygon([(sx0*C, (sy0+0.10)*C), (sx1*C, (sy0+0.10)*C), ((sx1-0.04)*C, sy1*C), ((sx0+0.04)*C, sy1*C)],
              fill=WINE, outline=INK, width=lw(6))
    d.rectangle([(sx0+0.02)*C, sy0*C, (sx1-0.02)*C, (sy0+0.10)*C], fill=GOLD, outline=INK, width=lw(6))
    # モーションライン（左右）
    for side in (-1, 1):
        for i, dy in enumerate([0.08, 0.20, 0.32]):
            x0 = (0.50 + side*(0.20 + i*0.02)) * C
            x1 = (0.50 + side*(0.32 + i*0.02)) * C
            y = (sy0 + dy) * C
            d.line([(x0, y), (x1, y - (0.03*C))], fill=GOLD, width=lw(7))
    # 泡（気泡）
    for bx, by, br in [(0.50, 0.20, 0.02), (0.44, 0.16, 0.015), (0.56, 0.15, 0.018)]:
        d.ellipse([(bx-br)*C, (by-br)*C, (bx+br)*C, (by+br)*C], fill=CREAM, outline=INK, width=lw(3))
    save(im, "shakerato_step3_shake.png")

# ---------- icon 8: ペアリング（モスカート/パッシート × エスプレッソ） ----------
def pairing_moscato_espresso():
    im = canvas(); d = ImageDraw.Draw(im)
    # ワイングラス（左）
    bcx, bowl_top, bowl_bot = 0.34, 0.16, 0.42
    d.pieslice([(bcx-0.13)*C, bowl_top*C, (bcx+0.13)*C, bowl_bot*C+0.10*C], start=0, end=180,
               fill=GOLD_SOFT, outline=INK, width=lw(6))
    d.line([(bcx*C, bowl_bot*C+0.02*C), (bcx*C, 0.64*C)], fill=INK, width=lw(6))
    d.line([((bcx-0.09)*C, 0.70*C), ((bcx+0.09)*C, 0.70*C)], fill=INK, width=lw(7))
    d.line([(bcx*C, 0.64*C), (bcx*C, 0.70*C)], fill=INK, width=lw(6))
    # エスプレッソカップ&ソーサー（右）
    cx0, cx1, cy0, cy1 = 0.58, 0.86, 0.46, 0.60
    d.rounded_rectangle([cx0*C, cy0*C, cx1*C, cy1*C], radius=int(0.02*C), fill=CREAM, outline=INK, width=lw(6))
    d.rectangle([cx0*C+lw(3), cy0*C+lw(3), cx1*C-lw(3), (cy0+0.05)*C], fill=WINE)
    d.arc([(cx1-0.02)*C, (cy0+0.02)*C, (cx1+0.09)*C, (cy0+0.10)*C], start=280, end=90, fill=INK, width=lw(6))
    d.ellipse([0.52*C, 0.62*C, 0.92*C, 0.67*C], fill=CREAM, outline=INK, width=lw(6))
    save(im, "pairing_moscato_espresso.png")

# ---------- icon 9: 酸味が前に出る（レモンスライス＋つんとした酸のトゲ＋上向き矢印） ----------
def acidity_lemon():
    im = canvas(); d = ImageDraw.Draw(im)
    cx, cy, r = 0.46, 0.50, 0.26
    # 外皮（ゴールド）
    d.ellipse([(cx-r)*C, (cy-r)*C, (cx+r)*C, (cy+r)*C], fill=GOLD, outline=INK, width=lw(7))
    # 果肉（クリーム）
    r2 = r * 0.80
    d.ellipse([(cx-r2)*C, (cy-r2)*C, (cx+r2)*C, (cy+r2)*C], fill=CREAM, outline=INK, width=lw(4))
    # 果肉セグメント（放射状の線、8分割）
    segs = 8
    for i in range(segs):
        ang = 2 * math.pi * i / segs
        x2 = cx + r2 * 0.95 * math.cos(ang)
        y2 = cy + r2 * 0.95 * math.sin(ang)
        d.line([(cx*C, cy*C), (x2*C, y2*C)], fill=GOLD_SOFT, width=lw(5))
    d.ellipse([(cx-0.02)*C, (cy-0.02)*C, (cx+0.02)*C, (cy+0.02)*C], fill=GOLD, outline=INK, width=lw(3))
    # 酸味のトゲ（外周から放射、ワインレッド）＝つんとした酸味を表現
    for i in range(segs):
        ang = 2 * math.pi * (i + 0.5) / segs
        x1 = cx + r * 1.05 * math.cos(ang); y1 = cy + r * 1.05 * math.sin(ang)
        x2 = cx + r * 1.20 * math.cos(ang); y2 = cy + r * 1.20 * math.sin(ang)
        d.line([(x1*C, y1*C), (x2*C, y2*C)], fill=WINE, width=lw(6))
    # 上向き矢印（「前に出る」＝知覚が立ち上がるイメージ、右下）
    ax, ay = 0.80, 0.68
    d.polygon([(ax*C, (ay-0.14)*C), ((ax-0.055)*C, (ay-0.03)*C), ((ax+0.055)*C, (ay-0.03)*C)],
              fill=WINE, outline=INK, width=lw(4))
    d.rectangle([(ax-0.02)*C, (ay-0.03)*C, (ax+0.02)*C, (ay+0.10)*C], fill=WINE, outline=INK, width=lw(3))
    save(im, "acidity_lemon.png")

# ---------- icon 10: だから明るい酸が映える（エチオピア産コーヒーチェリー＋サンバースト） ----------
def bright_acidity():
    im = canvas(); d = ImageDraw.Draw(im)
    cx, cy = 0.50, 0.52
    # 背景の光線（明るさ＝ブライトな酸を表現／真上・真横を避けてオフセットし、
    # 上部の枝と重ならないようにする）
    rays = 12
    for i in range(rays):
        ang = 2 * math.pi * (i + 0.5) / rays
        x1 = cx + 0.22 * math.cos(ang); y1 = cy + 0.22 * math.sin(ang)
        x2 = cx + 0.41 * math.cos(ang); y2 = cy + 0.41 * math.sin(ang)
        d.line([(x1*C, y1*C), (x2*C, y2*C)], fill=GOLD, width=lw(7))
    # コーヒーチェリー2粒（完熟、ワインレッド）
    for dx, dy, r in [(-0.07, 0.05, 0.115), (0.08, 0.00, 0.12)]:
        ccx, ccy = cx + dx, cy + dy
        d.ellipse([(ccx-r)*C, (ccy-r)*C, (ccx+r)*C, (ccy+r)*C], fill=WINE, outline=INK, width=lw(6))
        hlx, hly, hr = ccx - r*0.35, ccy - r*0.35, r*0.24
        d.ellipse([(hlx-hr)*C, (hly-hr)*C, (hlx+hr)*C, (hly+hr)*C], fill=GOLD_SOFT)
        # 小さな柄（各チェリーの上端から短く、INKで最小限に）
        d.line([(ccx*C, (ccy-r*0.95)*C), (ccx*C, (ccy-r*1.35)*C)], fill=INK, width=lw(5))
    save(im, "bright_acidity.png")

if __name__ == "__main__":
    sicilia_granita()
    lecce_caffe()
    torino_bicerin()
    temperatura_aroma()
    shakerato_step1_espresso()
    shakerato_step2_shaker()
    shakerato_step3_shake()
    pairing_moscato_espresso()
    acidity_lemon()
    bright_acidity()
    print("done")
