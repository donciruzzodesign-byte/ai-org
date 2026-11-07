"""デスクトップの保存フォルダを、シリーズ・講座の回・州の粒度でワイン台帳へ初期登録する。

ファイルは移動・コピーせず、台帳には場所(絶対パス)だけを書く。2回実行しても重複しない。
`CHIAVE`(パスワード類)を含むパスは読まない。

使い方: python3 scripts/backfill_wine_vault.py [--archive パス] [--vault パス] [--dry-run]
"""
import argparse
import os
import re
import sys
import unicodedata
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import vault as vault_mod

DEFAULT_ARCHIVE = os.path.expanduser("~/Desktop/投稿内容・資料一式保存用フォルダー")
DEFAULT_VAULT = os.path.expanduser("~/Documents/ワイン台帳")

LESSON_RE = re.compile(r"^\d+[・\s]")
CAROUSEL_NAMES = {"trivia", "ワイン診断", "AISテイスティング方"}
GIFT_NAMES = {"公式LINE登録者プレゼント", "資料作成用アセット"}
LEDGER_OF = {"講座の回": "講座の回.md", "州別": "州別.md", "シリーズ": "シリーズ.md", "配布物": "配布物.md"}


def _blocked(name: str) -> bool:
    return "CHIAVE" in name


def _count_files(path: str) -> int:
    n = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and not _blocked(d)]
        n += sum(1 for f in files if not f.startswith(".") and not _blocked(f))
    return n


def _subdirs(path: str) -> list:
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return []
    return [n for n in names
            if not n.startswith(".") and not _blocked(n) and os.path.isdir(os.path.join(path, n))]


def _plan(archive: str) -> list:
    """(台帳キー, 名称, 種類, フォルダパス) の一覧を返す。"""
    items = []
    for raw in _subdirs(archive):
        path = os.path.join(archive, raw)
        name = unicodedata.normalize("NFC", raw)  # macOSは濁点などを分解形で持つため
        if "20州の旅" in name:
            items += [("州別", unicodedata.normalize("NFC", c), "州", os.path.join(path, c)) for c in _subdirs(path)]
        elif name == "リール素材":
            items += [("シリーズ", unicodedata.normalize("NFC", c), "リール", os.path.join(path, c)) for c in _subdirs(path)]
        elif name in CAROUSEL_NAMES:
            items.append(("シリーズ", name, "カルーセル/資料", path))
        elif name in GIFT_NAMES:
            items.append(("配布物", name, "配布物", path))
        elif LESSON_RE.match(name):
            items.append(("講座の回", name, "講座の回", path))
        else:
            items.append(("未分類", name, "要確認", path))
    return items


def _existing(vault: str, ledger_key: str) -> set:
    return {(r[0], r[4]) for r in vault_mod.read_rows(vault, LEDGER_OF[ledger_key], 10**6)}


def backfill(archive: str, vault: str, dry_run: bool = False) -> dict:
    counts = {"講座の回": 0, "州別": 0, "シリーズ": 0, "配布物": 0, "空": 0, "未分類": 0}
    seen = {k: _existing(vault, k) for k in LEDGER_OF}
    for key, name, kind, path in _plan(archive):
        n = _count_files(path)
        if n == 0:
            counts["空"] += 1
            continue
        if key == "未分類":
            counts["未分類"] += 1
            continue
        if (name, path) in seen[key]:
            continue
        date = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
        if not dry_run:
            vault_mod.append_row(vault, LEDGER_OF[key], [name, kind, f"{n}ファイル", date, path, "登録済み"])
        counts[key] += 1
    return counts


def _report(archive: str) -> None:
    for key, name, kind, path in _plan(archive):
        n = _count_files(path)
        tag = "空" if n == 0 else key
        print(f"  [{tag}] {name}（{n}ファイル）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=DEFAULT_ARCHIVE)
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        _report(args.archive)
    result = backfill(args.archive, args.vault, dry_run=args.dry_run)
    print(("予定(書き込みなし): " if args.dry_run else "追記: ") + str(result))
    if not args.dry_run:
        from scripts.build_wine_graph import build as build_wine_graph
        print("グラフ更新: " + str(build_wine_graph(args.vault)))
