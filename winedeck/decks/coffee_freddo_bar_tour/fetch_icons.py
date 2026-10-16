#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CUBOCCI STUDIO ブランドカラーのフラットイラストアイコンを gpt-image-1 で生成する。
1024x1024・透過背景・単一モチーフ・線画+フラット塗り。

使い方: python3 fetch_icons.py
"""
import os, sys, base64, json, requests

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = "/Users/kubotahironori/ai-org/.env"
OUT_DIR = "/Users/kubotahironori/ai-org/winedeck/decks/coffee_freddo_bar_tour/icons"

def load_env():
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

STYLE_PREFIX = (
    "A minimalist flat-illustration icon, hand-drawn line + flat color fill style, "
    "single centered motif, no text, no lettering, no background scenery, no shadow gradients. "
    "Color palette strictly limited to: wine red #6B1A2A, gold #C9A84C, cream #F5F0E8, "
    "and a soft off-white/cream background. Clean bold outlines, gentle rounded shapes, "
    "editorial infographic sticker style, square composition, centered with generous margin. "
)

ICONS = [
    {
        "out": "sicilia_granita.png",
        "prompt": STYLE_PREFIX + "Motif: a tall glass of Sicilian coffee granita (granita di caffè) "
                   "with a brioche col tuppo bun beside it, viewed from the side.",
    },
    {
        "out": "lecce_caffe.png",
        "prompt": STYLE_PREFIX + "Motif: a small glass of Caffè Leccese — iced espresso poured over "
                   "almond milk, with visible layered pale and dark tones, a straw resting on the glass.",
    },
    {
        "out": "torino_bicerin.png",
        "prompt": STYLE_PREFIX + "Motif: a Bicerin glass showing three distinct layers — dark coffee, "
                   "chocolate, and whipped cream on top, in a small clear glass cup.",
    },
    {
        "out": "temperatura_aroma.png",
        "prompt": STYLE_PREFIX + "Motif: a simple thermometer next to a coffee cup with visible steam "
                   "swirls fading into closed spiral lines, representing aroma opening and closing with temperature.",
    },
    {
        "out": "shakerato_step1_espresso.png",
        "prompt": STYLE_PREFIX + "Motif: an espresso machine portafilter pouring a thin stream of "
                   "espresso into a small cup, side view, simple and iconic.",
    },
    {
        "out": "shakerato_step2_shaker.png",
        "prompt": STYLE_PREFIX + "Motif: a cocktail shaker with ice cubes and a small sugar spoon beside it, "
                   "simple flat icon composition.",
    },
    {
        "out": "shakerato_step3_shake.png",
        "prompt": STYLE_PREFIX + "Motif: a cocktail shaker being shaken with motion lines and small foam "
                   "bubbles around it, dynamic but simple flat icon.",
    },
    {
        "out": "pairing_moscato_espresso.png",
        "prompt": STYLE_PREFIX + "Motif: a small glass of golden Moscato/Passito sweet wine beside a "
                   "classic espresso cup on a saucer, paired side by side.",
    },
]

def main():
    load_env()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set", file=sys.stderr); sys.exit(1)
    os.makedirs(OUT_DIR, exist_ok=True)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    for job in ICONS:
        out_path = os.path.join(OUT_DIR, job["out"])
        if os.path.exists(out_path):
            print(f"skip (exists): {job['out']}")
            continue
        payload = {
            "model": "gpt-image-1",
            "prompt": job["prompt"],
            "size": "1024x1024",
            "background": "transparent",
            "n": 1,
        }
        try:
            resp = requests.post("https://api.openai.com/v1/images/generations",
                                  headers=headers, json=payload, timeout=180)
            if resp.status_code != 200:
                print(f"[MISS] {job['out']}: {resp.status_code} {resp.text[:300]}")
                continue
            b64 = resp.json()["data"][0]["b64_json"]
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"OK  {job['out']}")
        except Exception as e:
            print(f"[MISS] {job['out']}: {e}")

if __name__ == "__main__":
    main()
