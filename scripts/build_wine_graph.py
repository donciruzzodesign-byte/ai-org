"""ワイン台帳から、Obsidianのグラフビュー用リンクメモ(州・品種・投稿)を作る。

台帳(01_台帳)は変更しない。`05_グラフ/` 配下のメモを毎回作り直すので、何度実行してもよい。
使い方: python3 scripts/build_wine_graph.py [--vault パス]
"""
import argparse
import os
import re
import sys
import unicodedata
from urllib.parse import quote

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import vault as vault_mod

DEFAULT_VAULT = os.path.expanduser("~/Documents/ワイン台帳")
GRAPH_DIR = "05_グラフ"
HUB = "イタリア20州"
MARK = "<!-- 自動生成: scripts/build_wine_graph.py。手で書き足す場合は本文の下に -->"

# 台帳の州フォルダ名(英語) → 州名(日本語)
REGIONS = {
    "Valle d`Aosta": "ヴァッレ・ダオスタ", "Piemonte": "ピエモンテ", "Lombardia": "ロンバルディア",
    "Veneto": "ヴェネト", "Trentino_alto_adige": "トレンティーノ・アルト・アディジェ",
    "Friuli_Venezia_Giulia": "フリウリ・ヴェネツィア・ジュリア", "Liguria": "リグーリア",
    "Emilia Romagna": "エミリア・ロマーニャ", "Toscana": "トスカーナ", "Umbria": "ウンブリア",
    "Marche": "マルケ", "Lazio": "ラツィオ", "Abruzzo": "アブルッツォ", "Molise": "モリーゼ",
    "Campania": "カンパーニア", "Puglia": "プーリア", "Basilicata": "バジリカータ",
    "Calabria": "カラブリア", "Sicilia": "シチリア", "Sardegna": "サルデーニャ",
}


# 名前に含まれていれば、その州の資料とみなす語(産地が明らかなものだけ)
ALIASES = {
    "キャンティ": "トスカーナ", "ブルネッロ": "トスカーナ", "ノービレ": "トスカーナ", "モレッリーノ": "トスカーナ",
    "サン・ジミニャーノ": "トスカーナ", "Tuscan": "トスカーナ", "アルバーニャ": "エミリア・ロマーニャ",
    "ピニョレット": "エミリア・ロマーニャ", "ピコリット": "フリウリ・ヴェネツィア・ジュリア",
}
# 台帳ファイル → (タグ, 保存フォルダ)
ITEM_LEDGERS = {"講座の回.md": ("講座の回", "講座の回"), "シリーズ.md": ("シリーズ", "シリーズ"), "配布物.md": ("配布物", "配布物")}


def _clean(s: str) -> str:
    return re.sub(r'[#^\[\]|\\/:]', "", s).strip()


def _region_of(folder_name: str):
    name = unicodedata.normalize("NFC", folder_name)
    for en, ja in REGIONS.items():
        if name.endswith(en):
            return ja
    return None


def parse_theme(theme: str, regions) -> tuple:
    """「ピエモンテ州のネッビオーロ」→ ("ピエモンテ", "ネッビオーロ")。見つからない要素は None。"""
    state = next((r for r in sorted(regions, key=len, reverse=True) if r in theme), None)
    variety = None
    if state:
        m = re.search(re.escape(state) + r"州?の(.+)$", theme)
        if m:
            variety = _clean(m.group(1)) or None
    return state, variety


def _write(path: str, lines: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join([MARK, ""] + lines) + "\n")


def _prune_generated(root: str) -> None:
    """前回の自動生成メモを消す(台帳から無くなった投稿・品種がグラフに残らないように)。手で作ったメモは消さない。"""
    for sub in ("投稿", "品種", "州", *[d for _, d in ITEM_LEDGERS.values()]):
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            path = os.path.join(d, name)
            if name.endswith(".md") and open(path, encoding="utf-8").read().startswith(MARK):
                os.remove(path)


def _states_in(name: str, regions) -> list:
    """名前に含まれる州(日本語名・英語名・ALIASES)を返す。"""
    n = unicodedata.normalize("NFC", name).lower()
    found = [ja for en, ja in REGIONS.items() if en.lower() in n or ja in name]
    found += [ja for key, ja in ALIASES.items() if key.lower() in n]
    return sorted(set(found))


def _finder_link(path: str) -> list:
    if not path.startswith("/"):
        return []
    return ["", f"保存場所: [Finderで開く](file://{quote(path)})", f"`{path}`"]


def build(vault: str) -> dict:
    root = os.path.join(vault, GRAPH_DIR)
    _prune_generated(root)
    folders = {}  # 州名 -> 資料フォルダの場所
    for r in vault_mod.read_rows(vault, "州別.md", 10**6):
        ja = _region_of(r[0])
        if ja:
            folders[ja] = r[4]

    states = {ja: {"varieties": set(), "posts": []} for ja in REGIONS.values()}
    varieties = {}  # 品種 -> {"states": set, "posts": []}
    post_names = []
    for r in vault_mod.read_rows(vault, "投稿テーマ.md", 10**6):
        theme, date = r[2], r[3]
        post = _clean(f"{date} {theme}")
        state, variety = parse_theme(theme, states)
        links = []
        if state:
            states[state]["posts"].append(post)
            links.append(f"州: [[{state}]]")
        if variety:
            varieties.setdefault(variety, {"states": set(), "posts": []})["posts"].append(post)
            links.append(f"品種: [[{variety}]]")
            if state:
                states[state]["varieties"].add(variety)
                varieties[variety]["states"].add(state)
        _write(os.path.join(root, "投稿", post + ".md"),
               ["#投稿", "", f"# {theme}", "", f"- 作成日: {date}", f"- 記録元: [[投稿テーマ]]"] + [f"- {x}" for x in links])
        post_names.append(post)

    item_count = 0
    for ledger, (tag, sub) in ITEM_LEDGERS.items():
        for r in vault_mod.read_rows(vault, ledger, 10**6):
            name = _clean(r[0])
            linked = _states_in(r[0], states)
            for st in linked:
                states[st].setdefault("items", []).append(name)
            lines = [f"#{tag}", "", f"# {r[0]}", "", f"- 親: [[{ledger[:-3]}]]", f"- 種類: {r[1]}", f"- 作成日: {r[3]}"]
            lines += [f"- 州: [[{st}]]" for st in linked] + _finder_link(r[4])
            _write(os.path.join(root, sub, name + ".md"), lines)
            item_count += 1

    _write(os.path.join(root, HUB + ".md"),
           ["#ハブ", "", f"# {HUB}", ""] + [f"- [[{s}]]" for s in states])
    for s, d in states.items():
        lines = ["#州", "", f"# {s}", "", f"- 親: [[{HUB}]]"]
        lines += [f"- 品種: [[{v}]]" for v in sorted(d["varieties"])]
        lines += [f"- 投稿: [[{p}]]" for p in d["posts"]]
        lines += [f"- 資料: [[{i}]]" for i in sorted(d.get("items", []))]
        if s in folders:
            lines += ["", f"資料フォルダ: [Finderで開く](file://{quote(folders[s])})", f"`{folders[s]}`"]
        _write(os.path.join(root, "州", s + ".md"), lines)
    for v, d in varieties.items():
        lines = ["#品種", "", f"# {v}", ""]
        lines += [f"- 産地: [[{s}]]" for s in sorted(d["states"])]
        lines += [f"- 投稿: [[{p}]]" for p in d["posts"]]
        _write(os.path.join(root, "品種", v + ".md"), lines)
    return {"州": len(states), "品種": len(varieties), "投稿": len(post_names), "資料": item_count}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    print(build(ap.parse_args().vault))
