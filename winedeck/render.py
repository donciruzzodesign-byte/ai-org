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
    {"kind": "bullets", "eyebrow": "..", "title": "..",
     "items": [["見出し","補足"], ["見出し","補足","icons/xxx.png"], ...]},
    {"kind": "timeline", "eyebrow": "..", "title": "..", "events": [["年","出来事"], ...]},
    {"kind": "summary", "title": "..", "points": ["..",".."], "cta": "..", "sub": "..",
     "icon": "icons/xxx.png"},
    {"kind": "icon_grid", "eyebrow": "..", "title": "..", "cols": 2,
     "items": [["見出し","補足"], ["見出し","補足","icons/xxx.png"], ...], "closing": ".."},
    {"kind": "flow", "eyebrow": "..", "title": "..",
     "steps": ["..", ["..", "icons/xxx.png"], ".."], "closing": ".."},
    {"kind": "ranking", "eyebrow": "..", "title": "..",
     "items": [["1","見出し","補足"], ["2","見出し","補足","icons/xxx.png"], ...], "closing": ".."},
    {"kind": "quadrant", "eyebrow": "..", "title": "..",
     "x_axis": ["左ラベル","右ラベル"], "y_axis": ["下ラベル","上ラベル"],
     "points": [["ラベル", 0.2, 0.8], ...]}
  ]
}
# icon_grid/flow/ranking/quadrant は wine_type に "brand" を指定すると、ワインタイプに
# 紐づかない汎用インフォグラフィック用の CUBOCCI STUDIO ブランドカラーになる。

注意:
- 日本語は自動折り返ししません。1行の目安は下記 LIMITS 参照（超過すると警告を出します）。
- icon / photo に渡すパスは spec ファイル（このJSON）からの相対パス。存在しなければ [warn] を出し
  そのフィールドはアイコン無し（従来の番号バッジ/丸ポイント）にフォールバックする。
- num/total は並び順から自動採番（cover にはフッター無し）。
- --outdir 省略時のデフォルトは ~/Desktop/CUBOCCI_STUDIO/weekly/{--date}-wine/carousel/
  （--date 省略時は実行日）。--outdir を明示すればそちらを優先。
"""
import sys, json, argparse, os, datetime, base64, mimetypes
import winedeck as wd

# 1行あたりの全角換算・目安（枠内に収まる上限の実測ベース）
LIMITS = {
    "q": 12, "answer": 12, "subtitle": 16,        # cover
    "title": 13, "value": 26, "note": 30,         # 中面
    "event": 26, "point": 24, "head": 18,
    "name_it": 20, "name_kana": 14, "origin": 16, "feature": 16,
    "pair_name": 15, "pair_note": 17,             # profile
    "step": 22,                                   # flow
    "rank_head": 18, "rank_note": 24,             # ranking
    "axis": 12, "point_label": 10,                # quadrant
    "cmp_label": 13, "cmp_sub": 18, "cmp_body": 22, "cmp_tag": 14,  # compare
    "seq_label": 10, "headline": 16,              # sequence
}

_SPEC_DIR = None  # build() 実行中にセットする、photo相対パス解決用

def _data_uri(path):
    if not path:
        return None
    full = path if os.path.isabs(path) else os.path.join(_SPEC_DIR, path)
    if not os.path.exists(full):
        warn(f"photo not found: {full}")
        return None
    mime = mimetypes.guess_type(full)[0] or "image/jpeg"
    with open(full, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"

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

def build(spec, spec_dir=None):
    global _SPEC_DIR
    _SPEC_DIR = spec_dir or os.getcwd()
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
                                   swipe=s.get("swipe", "スワイプで解説 →"),
                                   bottle_photo=_data_uri(s.get("bottle_photo"))))
        elif kind == "rows":
            _check_len("title", s["title"], LIMITS["title"])
            for _, v in s["rows"]: _check_len("value", v, LIMITS["value"])
            slides.append(wd.rows_slide(wt, s["eyebrow"], s["title"],
                          [tuple(r) for r in s["rows"]], num=i, total=total,
                          grape=grape, closing=s.get("closing")))
        elif kind == "bullets":
            _check_len("title", s["title"], LIMITS["title"])
            items = []
            for it in s["items"]:
                h, n_ = it[0], it[1]
                _check_len("head", h, LIMITS["head"]); _check_len("note", n_, LIMITS["note"])
                if len(it) >= 3 and it[2]:
                    items.append((h, n_, _data_uri(it[2])))
                else:
                    items.append((h, n_))
            slides.append(wd.bullets_slide(wt, s["eyebrow"], s["title"],
                          items, num=i, total=total,
                          grape=grape, closing=s.get("closing")))
        elif kind == "timeline":
            for _, e in s["events"]: _check_len("event", e, LIMITS["event"])
            slides.append(wd.timeline_slide(wt, s["eyebrow"], s["title"],
                          [tuple(e) for e in s["events"]], num=i, total=total,
                          grape=grape, closing=s.get("closing")))
        elif kind == "summary":
            for pt in s["points"]: _check_len("point", pt, LIMITS["point"])
            slides.append(wd.summary_slide(wt, s["title"], s["points"],
                          cta=s.get("cta"), sub=s.get("sub"), num=i, total=total, grape=grape,
                          icon=_data_uri(s.get("icon"))))
        elif kind == "profile":
            _check_len("name_it", s["name_it"], LIMITS["name_it"])
            _check_len("name_kana", s["name_kana"], LIMITS["name_kana"])
            for line in s["origin"]: _check_len("origin", line, LIMITS["origin"])
            for line in s["feature"]: _check_len("feature", line, LIMITS["feature"])
            local = dict(s["local"]); jp = dict(s["jp"])
            for d, label in ((local, "local"), (jp, "jp")):
                _check_len(f"{label}.name", d["name"], LIMITS["pair_name"])
                _check_len(f"{label}.note", d["note"], LIMITS["pair_note"])
                d["photo"] = _data_uri(d.get("photo"))
            slides.append(wd.profile_slide(wt, s["eyebrow"], s["name_it"], s["name_kana"],
                          _data_uri(s.get("grape_photo")), s["origin"], s["feature"],
                          local, jp, num=i, total=total, grape=grape))
        elif kind == "icon_grid":
            _check_len("title", s["title"], LIMITS["title"])
            items = []
            for it in s["items"]:
                h, n_ = it[0], it[1]
                _check_len("head", h, LIMITS["head"]); _check_len("note", n_, LIMITS["note"])
                if len(it) >= 3 and it[2]:
                    items.append((h, n_, _data_uri(it[2])))
                else:
                    items.append((h, n_))
            slides.append(wd.icon_grid_slide(wt, s["eyebrow"], s["title"],
                          items, cols=s.get("cols", 2),
                          num=i, total=total, grape=grape, closing=s.get("closing")))
        elif kind == "flow":
            steps = []
            for st in s["steps"]:
                if isinstance(st, list):
                    text = st[0]; icon = st[1] if len(st) > 1 else None
                    _check_len("step", text, LIMITS["step"])
                    steps.append([text, _data_uri(icon)] if icon else [text])
                else:
                    _check_len("step", st, LIMITS["step"])
                    steps.append(st)
            slides.append(wd.flow_slide(wt, s["eyebrow"], s["title"], steps,
                          num=i, total=total, grape=grape, closing=s.get("closing")))
        elif kind == "ranking":
            items = []
            for it in s["items"]:
                r, h, n_ = it[0], it[1], it[2]
                _check_len("rank_head", h, LIMITS["rank_head"])
                _check_len("rank_note", n_, LIMITS["rank_note"])
                if len(it) >= 4 and it[3]:
                    items.append((r, h, n_, _data_uri(it[3])))
                else:
                    items.append((r, h, n_))
            slides.append(wd.ranking_slide(wt, s["eyebrow"], s["title"],
                          items, num=i, total=total, grape=grape,
                          closing=s.get("closing")))
        elif kind == "compare":
            sides = []
            for key in ("left", "right"):
                side = dict(s[key])
                _check_len("cmp_label", side["label"], LIMITS["cmp_label"])
                if side.get("sublabel"): _check_len("cmp_sub", side["sublabel"], LIMITS["cmp_sub"])
                for line in side.get("body", []): _check_len("cmp_body", line, LIMITS["cmp_body"])
                if side.get("tag"): _check_len("cmp_tag", side["tag"], LIMITS["cmp_tag"])
                side["photo"] = _data_uri(side.get("photo"))
                sides.append(side)
            slides.append(wd.compare_slide(wt, s["eyebrow"], s["title"], sides[0], sides[1],
                          num=i, total=total, grape=grape, closing=s.get("closing")))
        elif kind == "sequence":
            if s.get("headline"): _check_len("headline", s["headline"], LIMITS["headline"])
            nodes = []
            for nd in s["nodes"]:
                node = dict(nd)
                for line in node.get("label", "").split("\n"):
                    _check_len("seq_label", line, LIMITS["seq_label"])
                node["icon"] = _data_uri(node.get("icon"))
                nodes.append(node)
            slides.append(wd.sequence_slide(wt, s["eyebrow"], s["title"], nodes,
                          headline=s.get("headline"), num=i, total=total, grape=grape,
                          closing=s.get("closing")))
        elif kind == "region_map":
            pins = []
            for pin in s["pins"]:
                np_ = dict(pin)
                np_["photo"] = _data_uri(np_.get("photo"))
                pins.append(np_)
            map_aspect = 1.0
            map_path = s.get("map_photo")
            if map_path:
                full = map_path if os.path.isabs(map_path) else os.path.join(_SPEC_DIR, map_path)
                if os.path.exists(full):
                    try:
                        from PIL import Image
                        with Image.open(full) as im:
                            map_aspect = im.width / im.height
                    except Exception as e:
                        warn(f"map_photo のサイズ取得に失敗、正方形として扱う: {e}")
            slides.append(wd.region_map_slide(wt, s["eyebrow"], s["title"],
                          _data_uri(s.get("map_photo")), pins, closing=s.get("closing"),
                          num=i, total=total, grape=grape, map_aspect=map_aspect,
                          legend_cols=s.get("legend_cols", 4)))
        elif kind == "myth":
            boxes = []
            for box in s["boxes"]:
                nb = dict(box)
                items = []
                for it in box.get("items", []):
                    ni = dict(it)
                    ni["icon"] = _data_uri(ni.get("icon"))
                    items.append(ni)
                nb["items"] = items
                boxes.append(nb)
            slides.append(wd.myth_slide(wt, s["title_main"], s["title_neg"], s["title_pos"],
                          _data_uri(s.get("center_photo")), boxes, closing=s.get("closing"),
                          num=i, total=total, grape=grape))
        elif kind == "quadrant":
            for lbl, _, _ in s["points"]: _check_len("point_label", lbl, LIMITS["point_label"])
            for lbl in list(s["x_axis"]) + list(s["y_axis"]):
                _check_len("axis", lbl, LIMITS["axis"])
            slides.append(wd.quadrant_slide(wt, s["eyebrow"], s["title"],
                          tuple(s["x_axis"]), tuple(s["y_axis"]),
                          [tuple(pt) for pt in s["points"]], num=i, total=total, grape=grape))
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
    name, slides = build(spec, spec_dir=os.path.dirname(os.path.abspath(args.spec)))
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
