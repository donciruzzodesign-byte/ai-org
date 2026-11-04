"""ワイン台帳(Obsidian保管庫)の骨組みを作る。既存ファイルは上書きしない(何度実行しても安全)。

使い方: `python3 scripts/init_wine_vault.py [パス]`  既定: ~/Documents/ワイン台帳
"""
import os
import sys

LEDGERS = ["シリーズ", "講座の回", "州別", "投稿テーマ", "配布物", "B-roll"]

ROW_FORMAT = "名称｜種類｜切り口(一言)｜作成日｜場所(パスまたはURL)｜使用状況"
BROLL_FORMAT = "取得日｜キーワード｜映像の説明語｜Pexels動画ID｜保存先"

RULES = f"""# ワイン台帳のルール(すべてのAIが最初に読む)

ai-org・Claudeアプリ・手作業の資料で、似たものを重ねないための共通の記憶です。

## 作業の流れ(確認 → 着手 → 記録)
1. **作る前に確認**：`01_台帳/` と `02_進行中.md` を読み、同じ・似た切り口がないか確かめる。
2. **着手時に宣言**：`02_進行中.md` に「誰が・何を・いつから」を1行書く。
3. **完了時に記録**：`01_台帳/` の該当ファイルへ1行追記し、`02_進行中.md` の行を消す。

## 1行の形式
- 通常：`{ROW_FORMAT}`
- `B-roll.md`：`{BROLL_FORMAT}`

## 守ること
- `B-roll.md` と `投稿テーマ.md` は ai-org が追記する**追記専用**ファイル。手で編集しない。
- パスワード・APIキー・口座情報などは、この保管庫に絶対に書かない。
- デスクトップの資料は移動せず、台帳には「場所」だけを書く。
- コーヒーの件は `AI会社` 保管庫で管理する(ここには書かない)。
"""

DECISIONS = """# 決めごと

- 企画名：「イタリアワイン、迷わない私になる」8日間プロジェクト
- 講座：案B(4週間グループ講座・週1回60分Zoom・全4回・録画あり・LINEオープンチャット)
  - 価格 14,800円・定員 15名は**仮置き**(未確定)
- コーヒー：`AI会社` 保管庫に一本化。ai-org のコーヒー自動実行は停止中。
"""

FILES = {
    "00_ルール.md": RULES,
    "02_進行中.md": "# 進行中\n\n着手前にここへ宣言し、完了したら消す。\n\n形式：`誰｜何を｜開始日`\n",
    "03_決めごと.md": DECISIONS,
}


def init_vault(path: str) -> list:
    """保管庫を作り、新規に作ったパスの一覧を返す。既存は上書きしない。"""
    created = []

    def _write(rel: str, text: str) -> None:
        full = os.path.join(path, rel)
        if os.path.exists(full):
            return
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        created.append(full)

    for rel, text in FILES.items():
        _write(rel, text)
    for name in LEDGERS:
        fmt = BROLL_FORMAT if name == "B-roll" else ROW_FORMAT
        _write(os.path.join("01_台帳", f"{name}.md"), f"# {name}.md\n# {fmt}\n")
    promo = os.path.join(path, "04_プロモーション")
    if not os.path.isdir(promo):
        os.makedirs(promo)
        created.append(promo)
    return created


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/ワイン台帳")
    made = init_vault(target)
    print(f"保管庫: {target}")
    print(f"新規作成 {len(made)} 件" if made else "すべて作成済み(変更なし)")
