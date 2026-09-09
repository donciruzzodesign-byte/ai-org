#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pexelsからブドウ／料理写真を検索・ダウンロードし、カード埋め込み用に
リサイズ・再圧縮してphotos/に保存する。

使い方:
    python3 fetch_photos.py jobs.json
    jobs.json = [{"out": "barbera_grape.jpg", "query": "red wine grapes vineyard",
                  "orientation": "landscape", "size": [900, 340]}, ...]
"""
import sys, os, json, io, time
import requests
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(HERE, "photos")

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def search_pexels(query, api_key, orientation="landscape"):
    r = requests.get("https://api.pexels.com/v1/search",
                      headers={"Authorization": api_key},
                      params={"query": query, "per_page": 5, "orientation": orientation},
                      timeout=20)
    r.raise_for_status()
    photos = r.json().get("photos", [])
    return photos[0] if photos else None

def fetch_one(job, api_key):
    out = os.path.join(PHOTO_DIR, job["out"])
    if os.path.exists(out) and not job.get("force"):
        print(f"skip (exists): {job['out']}")
        return True
    photo = search_pexels(job["query"], api_key, job.get("orientation", "landscape"))
    if not photo:
        print(f"[MISS] no result for: {job['query']}")
        return False
    src_url = photo["src"].get("large") or photo["src"].get("medium")
    img_r = requests.get(src_url, timeout=30)
    img_r.raise_for_status()
    im = Image.open(io.BytesIO(img_r.content)).convert("RGB")
    w, h = job.get("size", [600, 400])
    # センタークロップしてから指定サイズへ
    src_ratio = im.width / im.height
    tgt_ratio = w / h
    if src_ratio > tgt_ratio:
        new_w = int(im.height * tgt_ratio)
        x0 = (im.width - new_w) // 2
        im = im.crop((x0, 0, x0 + new_w, im.height))
    else:
        new_h = int(im.width / tgt_ratio)
        y0 = (im.height - new_h) // 2
        im = im.crop((0, y0, im.width, y0 + new_h))
    im = im.resize((w, h), Image.LANCZOS)
    os.makedirs(PHOTO_DIR, exist_ok=True)
    im.save(out, "JPEG", quality=76, optimize=True)
    print(f"OK  {job['out']}  <- {job['query']}  (pexels photographer: {photo.get('photographer')})")
    return True

def main():
    load_env()
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        print("PEXELS_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        jobs = json.load(f)
    ok = 0
    for job in jobs:
        try:
            if fetch_one(job, api_key):
                ok += 1
        except Exception as e:
            print(f"[ERR] {job['out']}: {e}")
        time.sleep(0.15)
    print(f"done: {ok}/{len(jobs)}")

if __name__ == "__main__":
    main()
