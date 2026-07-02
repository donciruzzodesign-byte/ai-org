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
