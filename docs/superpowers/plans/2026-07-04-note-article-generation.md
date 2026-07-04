# note原稿自動生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 火曜の週次パイプラインに、creator エージェントによる note 記事原稿の自動生成タスク（ワイン・コーヒー各1本）を追加し、`output/YYYY-MM-DD-{wine|coffee}/note_article.md` に保存する。

**Architecture:** 既存の runner タスクパターン（`_read_todays_log()` → `run_agent()` → 出力保存）を踏襲。新エージェントは作らず creator に note 記事化プロンプトを渡す。ファイル書き出しは新ヘルパー `_write_note_article()` に分離してユニットテスト対象にする。

**Tech Stack:** Python 3 / schedule ライブラリ / pytest（unittest.mock）

**Spec:** `docs/superpowers/specs/2026-07-04-note-integration-design.md`

## Global Constraints

- note への自動投稿は実装しない（原稿ファイル生成まで。投稿は手動コピペ）
- 新しいエージェント定義・新しい依存ライブラリを追加しない
- 各タスク関数は既存タスクと同様に try/except で包み、失敗しても他タスクへ影響させない
- スケジュール: ワイン note 記事 = 火曜 13:00、コーヒー note 記事 = 火曜 13:30
- 出力先: `output/YYYY-MM-DD-wine/note_article.md` / `output/YYYY-MM-DD-coffee/note_article.md`
- テスト実行コマンド: `python3 -m pytest tests/ -v`（プロジェクトルート `/Users/kubotahironori/ai-org` で実行）

---

### Task 1: `_write_note_article` ヘルパー

**Files:**
- Modify: `runner.py`（`_read_todays_log` の直後、`monday_task` の直前に追加。現在の行番号で 112 行目付近）
- Test: `tests/test_runner_note.py`（新規作成）

**Interfaces:**
- Consumes: なし（標準ライブラリ `os` のみ。`runner.py` 冒頭で import 済み）
- Produces: `_write_note_article(text: str, output_dir: str) -> str` — `output_dir` を必要なら作成し、`note_article.md` に `text` を UTF-8 で書き込み、書き込んだファイルのフルパスを返す。Task 2 のタスク関数がこれを呼ぶ。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_runner_note.py` を新規作成:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from runner import _write_note_article


def test_write_note_article_creates_file(tmp_path):
    output_dir = str(tmp_path / "2026-07-07-wine")
    path = _write_note_article("# タイトル案\n\n記事本文", output_dir)

    assert path == os.path.join(output_dir, "note_article.md")
    with open(path, encoding="utf-8") as f:
        assert f.read() == "# タイトル案\n\n記事本文"


def test_write_note_article_creates_missing_dir(tmp_path):
    """videoタスクが失敗して出力ディレクトリが無くても書き込める。"""
    output_dir = str(tmp_path / "not" / "yet" / "created")
    path = _write_note_article("本文", output_dir)

    assert os.path.isfile(path)
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_runner_note.py -v`
Expected: FAIL — `ImportError: cannot import name '_write_note_article' from 'runner'`

- [ ] **Step 3: 最小実装を書く**

`runner.py` の `_read_todays_log()` 関数の直後（`def monday_task():` の前）に追加:

```python
def _write_note_article(text: str, output_dir: str) -> str:
    """note記事原稿を output_dir/note_article.md に保存し、パスを返す。"""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "note_article.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_runner_note.py -v`
Expected: PASS（2件）

- [ ] **Step 5: コミット**

```bash
git add runner.py tests/test_runner_note.py
git commit -m "feat: note記事原稿の書き出しヘルパー _write_note_article を追加"
```

---

### Task 2: note記事作成タスクとスケジュール登録

**Files:**
- Modify: `runner.py`（`coffee_friday_task` の直後・`main()` の前にタスク関数を追加。`main()` 内にスケジュール登録と起動メッセージ1行を追加）
- Test: `tests/test_runner_note.py`（テスト追記）

**Interfaces:**
- Consumes: `_write_note_article(text, output_dir) -> str`（Task 1）、既存の `_read_todays_log() -> str`、`run_agent(agent_name, prompt, label) -> str`
- Produces: `_note_article_prompt(context: str, drink_label: str, fallback_theme: str) -> str` / `tuesday_note_task()` / `coffee_tuesday_note_task()`（引数なし・戻り値なし。schedule から呼ばれる）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_runner_note.py` の末尾に追記:

```python
from unittest.mock import patch


def test_note_task_functions_are_callable():
    import runner
    assert callable(runner.tuesday_note_task), "tuesday_note_task が存在しません"
    assert callable(runner.coffee_tuesday_note_task), "coffee_tuesday_note_task が存在しません"


def test_note_article_prompt_contains_context_and_format():
    import runner
    prompt = runner._note_article_prompt("今週のテーマ：バローロ", "ワイン", "既定テーマ")
    assert "今週のテーマ：バローロ" in prompt
    assert "タイトル案" in prompt
    assert "ハッシュタグ" in prompt
    assert "既定テーマ" in prompt


def test_tuesday_note_task_writes_article(tmp_path):
    """run_agent の戻り値が output/YYYY-MM-DD-wine/note_article.md に保存される。"""
    import runner
    from datetime import datetime

    with patch("runner.__file__", str(tmp_path / "runner.py")), \
         patch("runner.run_agent", return_value="note記事本文") as mock_run:
        runner.tuesday_note_task()

    mock_run.assert_called_once()
    assert mock_run.call_args.args[0] == "creator"

    date_str = datetime.now().strftime("%Y-%m-%d")
    article_path = tmp_path / "output" / f"{date_str}-wine" / "note_article.md"
    assert article_path.is_file()
    assert article_path.read_text(encoding="utf-8") == "note記事本文"


def test_coffee_tuesday_note_task_writes_article(tmp_path):
    import runner
    from datetime import datetime

    with patch("runner.__file__", str(tmp_path / "runner.py")), \
         patch("runner.run_agent", return_value="コーヒーnote記事本文"):
        runner.coffee_tuesday_note_task()

    date_str = datetime.now().strftime("%Y-%m-%d")
    article_path = tmp_path / "output" / f"{date_str}-coffee" / "note_article.md"
    assert article_path.is_file()


def test_note_tasks_catch_exceptions():
    """run_agent が失敗してもタスク関数は例外を外に漏らさない。"""
    import runner
    with patch("runner.run_agent", side_effect=Exception("API error")):
        runner.tuesday_note_task()
        runner.coffee_tuesday_note_task()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_runner_note.py -v`
Expected: 新規5件が FAIL（`AttributeError: module 'runner' has no attribute 'tuesday_note_task'` など）。Task 1 の2件は PASS のまま。

- [ ] **Step 3: タスク関数を実装する**

`runner.py` の `coffee_friday_task()` の直後（`def main():` の前）に追加:

```python
def _note_article_prompt(context: str, drink_label: str, fallback_theme: str) -> str:
    return (
        f"以下は今週の{drink_label}コンテンツのログ（テーマ提案・動画台本など）です。\n\n"
        f"{context}\n\n"
        f"上記の動画台本をもとに、動画を見なくても単体の読み物として成立する note 記事を作成してください。"
        f"台本がない場合はテーマ情報から作成し、テーマ情報もない場合は「{fallback_theme}」で作成してください。\n\n"
        "【読者】30〜50代女性。話し言葉の台本を、noteにふさわしい丁寧な書き言葉に整えてください。\n\n"
        "【出力形式】以下の4セクションをこの順で、Markdownで出力してください。\n"
        "## 投稿メモ\n"
        "- 見出し画像: images/scene_01.png を使用\n"
        "- 推奨公開日: 土曜（動画公開と同日）\n\n"
        "## タイトル案\n"
        "noteの検索・おすすめ面を意識したタイトルを3案\n\n"
        "## 本文\n"
        "2,000〜3,000字。## 見出しで区切り、リード → 本編 → まとめ → YouTube動画への誘導CTA の構成\n\n"
        "## ハッシュタグ\n"
        "note用ハッシュタグを5〜8個"
    )


def tuesday_note_task():
    try:
        context = _read_todays_log()
        prompt = _note_article_prompt(context, "ワイン", "イタリアワインの基本：品種と産地の覚え方")
        article = run_agent("creator", prompt, "火曜：note記事作成（ワイン）")
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"{date_str}-wine")
        path = _write_note_article(article, output_dir)
        print(f"  📝 note記事保存: {path}")
    except Exception as e:
        print(f"  ❌ 火曜：note記事作成（ワイン） 失敗: {e}")


def coffee_tuesday_note_task():
    try:
        context = _read_todays_log()
        prompt = _note_article_prompt(context, "コーヒー", "イタリアコーヒーの基本：エスプレッソ文化とバールの楽しみ方")
        article = run_agent("creator", prompt, "火曜：note記事作成（コーヒー）")
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"{date_str}-coffee")
        path = _write_note_article(article, output_dir)
        print(f"  📝 note記事保存: {path}")
    except Exception as e:
        print(f"  ❌ 火曜：note記事作成（コーヒー） 失敗: {e}")
```

注意: `tuesday_note_task` / `coffee_tuesday_note_task` 内では `os.path.dirname(os.path.abspath(__file__))` ではなく、既存タスクと同じく `runner.__file__` が patch できるように**関数内で** `os.path.dirname(os.path.abspath(__file__))` を評価する（上記コードの通り。モジュールレベル定数にしないこと）。

`main()` 内のスケジュール登録ブロック（`schedule.every().tuesday.at("10:30").do(coffee_tuesday_express_task)` の行の直後）に追加:

```python
    schedule.every().tuesday.at("13:00").do(tuesday_note_task)
    schedule.every().tuesday.at("13:30").do(coffee_tuesday_note_task)
```

`main()` 内の起動メッセージ `print("火 09:30 ワインExpress素材 / 火 10:30 コーヒーExpress素材")` の直後に追加:

```python
    print("火 13:00 ワインnote記事 / 火 13:30 コーヒーnote記事")
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_runner_note.py -v`
Expected: PASS（7件）

- [ ] **Step 5: 既存テストが壊れていないことを確認**

Run: `python3 -m pytest tests/ -v`
Expected: 全件 PASS（既存の失敗が元からある場合は、その失敗が増えていないこと）

- [ ] **Step 6: コミット**

```bash
git add runner.py tests/test_runner_note.py
git commit -m "feat: 火曜にnote記事原稿を自動生成するタスクを追加"
```

---

### Task 3: ドキュメント更新

**Files:**
- Modify: `CLAUDE.md`（週次スケジュール表・動画パイプライン出力表）

**Interfaces:**
- Consumes: Task 2 のタスク名・スケジュール時刻・出力ファイル名
- Produces: なし（ドキュメントのみ）

- [ ] **Step 1: CLAUDE.md の週次スケジュール表に2行追加**

`| 火 | 12:00 | コーヒー動画素材生成 | video |` の行の直後に追加:

```markdown
| 火 | 13:00 | ワインnote記事原稿生成 | creator |
| 火 | 13:30 | コーヒーnote記事原稿生成 | creator |
```

- [ ] **Step 2: CLAUDE.md の動画パイプライン出力表に1行追加**

`| auto_edit.jsx | AE自動配置スクリプト（File→Scripts→Run で実行） |` の行の直後に追加:

```markdown
| `note_article.md` | note記事原稿（投稿メモ・タイトル案・本文・ハッシュタグ。水曜レビュー時に手動でnoteへコピペ） |
```

- [ ] **Step 3: コミット**

```bash
git add CLAUDE.md
git commit -m "docs: note記事原稿生成タスクをCLAUDE.mdに反映"
```

---

## 手動検証（実装完了後・任意）

API を実際に呼ぶ動作確認（ANTHROPIC_API_KEY 必要・数十秒かかる）:

```bash
cd /Users/kubotahironori/ai-org
python3 -c "from runner import tuesday_note_task; tuesday_note_task()"
ls output/$(date +%Y-%m-%d)-wine/note_article.md
```

当日ログに台本がない曜日に実行した場合は、既定テーマ（フォールバック）で記事が生成されることも仕様どおり。
