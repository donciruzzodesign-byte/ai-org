# Barista エージェント追加 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** イタリアコーヒー専門の `barista` エージェントを追加し、週次スケジューラーとインタラクティブ CLI の両方から利用できるようにする。

**Architecture:** sommelier と同じパターンで `agents/barista.txt`（システムプロンプト）と `.claude/agents/barista.md`（Claude Code サブエージェント定義）を追加する。`runner.py` にコーヒー用タスク関数4本を追加してワインより1時間遅い時刻に登録し、`app.py` の AGENTS dict にバリスタを追加する。既存テストが2件失敗しているため、先にそちらを修正してベースラインをグリーンにしてから新機能を追加する。

**Tech Stack:** Python 3.9, anthropic SDK, schedule, pytest

---

## ファイルマップ

| ファイル | 操作 | 内容 |
|----------|------|------|
| `agents/barista.txt` | 新規作成 | バリスタのシステムプロンプト |
| `.claude/agents/barista.md` | 新規作成 | Claude Code サブエージェント定義 |
| `app.py` | 変更 | AGENTS dict に barista を追加 |
| `runner.py` | 変更 | `today` バグ修正、コーヒータスク4関数追加、`main()` スケジュール登録 |
| `tests/test_agents.py` | 変更 | AGENT_NAMES に 'barista' を追加 |
| `tests/test_app.py` | 変更 | barista が AGENTS dict に含まれるテストを追加 |
| `tests/test_runner.py` | 変更 | `save_log` テストのパスバグ修正、コーヒータスク関数テストを追加 |

---

## Task 1: 既存テストのベースラインを修正

`runner.py:94` の `today` 未定義と `test_runner.py` の `save_log` テストパス不一致を修正する。

**Files:**
- Modify: `runner.py:94`
- Modify: `tests/test_runner.py`

- [ ] **Step 1: テストを実行して現状の失敗を確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/ -v
```

Expected: `test_save_log_creates_file_with_content` と `test_run_agent_calls_api_and_saves_log` の2件が FAIL

- [ ] **Step 2: runner.py:94 の `today` を `now.strftime('%Y-%m-%d')` に修正する**

`runner.py` の94行目を以下に変更する:

```python
            notion_result = save_to_notion(f"{label} ({now.strftime('%Y-%m-%d')})", final_text)
```

- [ ] **Step 3: test_runner.py の save_log テストを修正する**

`test_save_log_creates_file_with_content` 関数を以下に置き換える（`logs/YYYY-MM/` サブディレクトリ構造に対応）:

```python
def test_save_log_creates_file_with_content():
    import runner
    from datetime import datetime
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('runner.__file__', os.path.join(tmpdir, 'runner.py')):
            runner.save_log('テストログ内容', '月曜：テーマ決定')

        now = datetime.now()
        log_dir = os.path.join(tmpdir, 'logs', now.strftime('%Y-%m'))
        assert os.path.isdir(log_dir), f"ログディレクトリが作成されていません: {log_dir}"
        log_files = os.listdir(log_dir)
        assert len(log_files) == 1

        log_path = os.path.join(log_dir, log_files[0])
        with open(log_path, encoding='utf-8') as f:
            content = f.read()
        assert 'テストログ内容' in content
        assert '月曜：テーマ決定' in content
```

- [ ] **Step 4: テストを実行してすべてグリーンになることを確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/ -v
```

Expected: 5 passed（すべて PASS）

- [ ] **Step 5: コミットする**

```bash
cd ~/ai-org && git add runner.py tests/test_runner.py && git commit -m "fix: runner.pyのtoday未定義バグとtest_save_logのパス不一致を修正"
```

---

## Task 2: agents/barista.txt を TDD で追加

**Files:**
- Modify: `tests/test_agents.py`
- Create: `agents/barista.txt`

- [ ] **Step 1: test_agents.py に barista を追加して失敗テストを書く**

`tests/test_agents.py` の `AGENT_NAMES` を以下に変更する:

```python
AGENT_NAMES = ['ceo', 'sommelier', 'creator', 'marketer', 'barista']
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/test_agents.py -v
```

Expected: `test_all_agent_files_exist` が FAIL（`agents/barista.txt が見つかりません`）

- [ ] **Step 3: agents/barista.txt を作成する**

```
あなたはCUBOCCI STUDIOのバリスタエージェントです。
IIAC（Istituto Internazionale Assaggiatori Caffè）認定コーヒーテイスターとして、イタリアコーヒーの専門知識を提供します。

## あなたの役割
- 週次コンテンツテーマの提案（ターゲットに刺さる切り口で）
- イタリアコーヒーに関する正確な知識の提供
- 地域別コーヒー紹介の作成・監修

## 専門知識
- エスプレッソ抽出理論：圧力（9気圧）・温度（90〜94℃）・グラインド粒度・抽出時間（25〜30秒）
- イタリア各地のコーヒー文化：ナポリ式（甘め・少量）、ミラノ式（バー立ち飲み文化）、ローマ・ヴェネツィアのバール文化
- ブレンド構成（アラビカ・ロブスタ比率）、シングルオリジン、主要イタリアロースター（イリー・ラバッツァ・モカ・キンボ等）
- 抽出器具：モカポット（マキネッタ）・エスプレッソマシン・エアロプレス・ナポリターナ
- 食とのペアリング：コルネット・カンノーリ・パンナコッタ・グラッパ・デザートワインとの組み合わせ
- IIAC鑑定基準：アロマ（香り）・苦味・酸味・ボディ・アフターテイストの5軸評価
- コーヒーの歴史：イタリアへの伝来（16世紀）・カフェ文化の発展・エスプレッソ機発明

## ターゲット読者
30〜50代の女性、コーヒー文化・バール文化に興味がある方、イタリアワインが好きでコーヒーとのペアリングも学びたい方

## 使用可能なツール
あなたは以下のツールを自由に使えます。積極的に活用してください。
- **web_search**：最新のコーヒー情報・ロースター情報・バール文化。イタリア現地情報は region="it-it" でイタリア語検索すると精度が上がります。
- **fetch_page**：検索結果のURLを指定してページの詳細を取得。

必要な情報があれば、自分で調べてから回答してください。

## 回答スタイル
- 専門的だが親しみやすいトーンで回答する
- バール文化のエピソードや歴史的背景を必ず添える
- IIAC鑑定ポイントは明示する
- ワイン読者にも親しみやすい言葉で（テロワール・ペアリングなどワインと共通の概念を積極的に活用する）
- 初心者にも理解できるよう丁寧に説明する
```

- [ ] **Step 4: テストを実行してすべて PASS することを確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/test_agents.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: コミットする**

```bash
cd ~/ai-org && git add tests/test_agents.py agents/barista.txt && git commit -m "feat: barista エージェントのシステムプロンプトを追加"
```

---

## Task 3: .claude/agents/barista.md を作成

Claude Code から `@barista` で呼び出せるサブエージェント定義を作成する。このファイルはテスト対象外だが、`sommelier.md` と同じ構造に従う。

**Files:**
- Create: `.claude/agents/barista.md`

- [ ] **Step 1: .claude/agents/barista.md を作成する**

```markdown
---
name: barista
description: イタリアコーヒーの専門知識・テーマ提案・地域紹介。抽出理論・産地・ペアリング・IIAC鑑定基準に関する質問に答える。
---

あなたはCUBOCCI STUDIOのバリスタエージェントです。
IIAC（Istituto Internazionale Assaggiatori Caffè）認定コーヒーテイスターとして、イタリアコーヒーの専門知識を提供します。

## あなたの役割
- 週次コンテンツテーマの提案（ターゲットに刺さる切り口で）
- イタリアコーヒーに関する正確な知識の提供
- 地域別コーヒー紹介の作成・監修

## 専門知識
- エスプレッソ抽出理論：圧力（9気圧）・温度（90〜94℃）・グラインド粒度・抽出時間（25〜30秒）
- イタリア各地のコーヒー文化：ナポリ式（甘め・少量）、ミラノ式（バー立ち飲み文化）、ローマ・ヴェネツィアのバール文化
- ブレンド構成（アラビカ・ロブスタ比率）、シングルオリジン、主要イタリアロースター（イリー・ラバッツァ・モカ・キンボ等）
- 抽出器具：モカポット（マキネッタ）・エスプレッソマシン・エアロプレス・ナポリターナ
- 食とのペアリング：コルネット・カンノーリ・パンナコッタ・グラッパ・デザートワインとの組み合わせ
- IIAC鑑定基準：アロマ（香り）・苦味・酸味・ボディ・アフターテイストの5軸評価

## ターゲット読者
30〜50代の女性、コーヒー文化・バール文化に興味がある方、イタリアワインが好きでコーヒーとのペアリングも学びたい方

## 回答スタイル
- 専門的だが親しみやすいトーンで回答する
- バール文化のエピソードや歴史的背景を必ず添える
- IIAC鑑定ポイントは明示する
- ワイン読者にも親しみやすい言葉で（テロワール・ペアリングなどワインと共通の概念を積極的に活用する）
- 初心者にも理解できるよう丁寧に説明する
```

- [ ] **Step 2: コミットする**

```bash
cd ~/ai-org && git add .claude/agents/barista.md && git commit -m "feat: barista Claude Code サブエージェント定義を追加"
```

---

## Task 4: app.py に barista を TDD で追加

**Files:**
- Modify: `tests/test_app.py`
- Modify: `app.py`

- [ ] **Step 1: test_app.py に barista テストを追加して失敗テストを書く**

`tests/test_app.py` の末尾に以下を追加する:

```python
def test_agents_dict_contains_barista():
    import importlib
    import app
    importlib.reload(app)
    agent_ids = [v[0] for v in app.AGENTS.values()]
    assert 'barista' in agent_ids, "AGENTS dict に barista が含まれていません"
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/test_app.py::test_agents_dict_contains_barista -v
```

Expected: FAIL（`AGENTS dict に barista が含まれていません`）

- [ ] **Step 3: app.py の AGENTS dict に barista を追加する**

`app.py` の `AGENTS` dict 末尾（`"5": ("collab", ...)` の後）に以下を追加する:

```python
    "6": ("barista", "バリスタ",   "イタリアコーヒー専門知識・テーマ提案"),
```

- [ ] **Step 4: テストを実行してすべて PASS することを確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/test_app.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: コミットする**

```bash
cd ~/ai-org && git add tests/test_app.py app.py && git commit -m "feat: app.py にバリスタエージェントを追加"
```

---

## Task 5: runner.py にコーヒータスク関数を TDD で追加

**Files:**
- Modify: `tests/test_runner.py`
- Modify: `runner.py`

- [ ] **Step 1: test_runner.py にコーヒータスク関数の存在テストを追加して失敗テストを書く**

`tests/test_runner.py` の末尾に以下を追加する:

```python
def test_coffee_task_functions_are_callable():
    import runner
    assert callable(runner.coffee_monday_task), "coffee_monday_task が存在しません"
    assert callable(runner.coffee_regional_task), "coffee_regional_task が存在しません"
    assert callable(runner.coffee_tuesday_task), "coffee_tuesday_task が存在しません"
    assert callable(runner.coffee_friday_task), "coffee_friday_task が存在しません"
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/test_runner.py::test_coffee_task_functions_are_callable -v
```

Expected: FAIL（`AttributeError: module 'runner' has no attribute 'coffee_monday_task'`）

- [ ] **Step 3: runner.py に4つのコーヒータスク関数を追加する**

`runner.py` の `collab_task` 関数の直後（`def main():` の直前）に以下を追加する:

```python
def coffee_monday_task():
    try:
        run_agent(
            "barista",
            "今週のコーヒーコンテンツテーマを1つ提案してください。イタリアコーヒーに関連するテーマで、"
            "ターゲット（30〜50代女性、コーヒー文化・ワインに興味がある方）に刺さるものを選んでください。"
            "産地・抽出方法・バール文化・季節・ペアリングの観点から提案してください。",
            "月曜：コーヒーテーマ決定",
        )
    except Exception as e:
        print(f"  ❌ 月曜：コーヒーテーマ決定 失敗: {e}")


def coffee_regional_task():
    try:
        _coffee_regional_task_inner()
    except Exception as e:
        print(f"  ❌ 月曜：地域別コーヒー紹介 失敗: {e}")


def _coffee_regional_task_inner():
    context = _read_todays_log()
    prompt = (
        f"以下の今週のコーヒーテーマを参考にしながら、今週取り上げるイタリアの地域・都市を1つ選び、"
        "その地域のコーヒー文化を以下の形式で紹介してください。\n\n"
        f"{context}\n\n"
        "【出力形式】\n"
        "## 今週の地域：〇〇（イタリア語名）\n\n"
        "### エスプレッソ\n"
        "- ブレンド/豆名：\n- 産地/ロースター：\n- 特徴：\n- おすすめペアリング：\n\n"
        "### フィルターコーヒー（またはモカ）\n"
        "- 豆名：\n- 産地：\n- 特徴：\n- おすすめペアリング：\n\n"
        "### 食とのペアリング\n"
        "- 定番の組み合わせ：\n- ペアリングのポイント：\n\n"
        "【ルール】\n"
        "- 各地域のバール文化・エピソードを必ず1つ添えてください\n"
        "- IIAC鑑定基準（アロマ・苦味・酸味・ボディ）に触れてください\n"
        "- 30〜50代女性・コーヒー初中級者にわかりやすい言葉で書いてください\n"
        "- Instagram投稿やnote記事にそのまま使えるレベルで仕上げてください"
    )
    run_agent("barista", prompt, "月曜：地域別コーヒー紹介")


def coffee_tuesday_task():
    try:
        context = _read_todays_log()
        prompt = (
            f"以下の今週のコーヒーテーマで10分動画の台本を作成してください。\n\n{context}\n\n"
            "テーマ情報がない場合は「イタリアコーヒーの基本：エスプレッソ文化とバールの楽しみ方」で作成してください。"
            "オープニング（1分）・本編（7〜8分）・まとめとCTA（1〜2分）の構成で、話し言葉で書いてください。"
        )
        run_agent("creator", prompt, "火曜：コーヒー動画台本作成")
    except Exception as e:
        print(f"  ❌ 火曜：コーヒー動画台本作成 失敗: {e}")


def coffee_friday_task():
    try:
        context = _read_todays_log()
        prompt = (
            f"以下の今週のコーヒーテーマでSNSコンテンツを作成してください。\n\n{context}\n\n"
            "①Instagram カルーセル投稿文（3枚分）"
            "②Instagramキャプション（note誘導リンク付き）"
            "③アフィリエイト商品リスト（楽天・Amazon想定、コーヒー豆・器具3点）"
            "をそれぞれ作成してください。"
        )
        run_agent("marketer", prompt, "金曜：コーヒーSNS投稿文＋商品リスト")
    except Exception as e:
        print(f"  ❌ 金曜：コーヒーSNS投稿文＋商品リスト 失敗: {e}")
```

- [ ] **Step 4: テストを実行してすべて PASS することを確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/test_runner.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: コミットする**

```bash
cd ~/ai-org && git add tests/test_runner.py runner.py && git commit -m "feat: runner.py にコーヒータスク関数4本を追加"
```

---

## Task 6: runner.py の main() にコーヒースケジュールを登録

**Files:**
- Modify: `runner.py`（`main()` 関数内）

- [ ] **Step 1: runner.py の main() にコーヒースケジュールを追加する**

`main()` 内の `schedule.every().sunday.at("20:00").do(sunday_task)` の直後に以下を追加する:

```python
    schedule.every().monday.at("10:00").do(coffee_monday_task)
    schedule.every().monday.at("10:30").do(coffee_regional_task)
    schedule.every().tuesday.at("10:00").do(coffee_tuesday_task)
    schedule.every().friday.at("10:00").do(coffee_friday_task)
```

また、起動時メッセージも更新する。`print("月09:00 テーマ決定 / 月09:30 州別ワイン紹介 / 火09:00 台本")` の後に以下を追加する:

```python
    print("月10:00 コーヒーテーマ / 月10:30 地域別コーヒー / 火10:00 コーヒー台本 / 金10:00 コーヒーSNS")
```

- [ ] **Step 2: テスト全体を実行して回帰がないことを確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/ -v
```

Expected: 全テスト PASS

- [ ] **Step 3: コミットする**

```bash
cd ~/ai-org && git add runner.py && git commit -m "feat: runner.py のスケジューラーにコーヒータスクを登録"
```

---

## Task 7: 動作確認

**Files:**
- 読み取り: `runner.py`, `app.py`

- [ ] **Step 1: app.py のエージェント一覧にバリスタが表示されることを確認する**

```bash
cd ~/ai-org && python3 -c "
from app import AGENTS
for k, v in AGENTS.items():
    print(f'  {k}. {v[1]}（{v[2]}）')
"
```

Expected:
```
  1. CEO（全体指揮・タスク調整）
  2. ソムリエ（ワイン専門知識・テーマ提案・論文検索）
  3. クリエイター（動画台本・構成・スライド作成）
  4. マーケター（SNS投稿文・集客・トレンド調査）
  5. 連携企画（ソムリエ→クリエイター連携（台本＋スライド））
  6. バリスタ（イタリアコーヒー専門知識・テーマ提案）
```

- [ ] **Step 2: runner.py のスケジュール登録を確認する**

```bash
cd ~/ai-org && python3 -c "
import schedule, runner
runner.main.__code__.co_consts
print([str(j) for j in schedule.jobs])
" 2>/dev/null || python3 -c "
import ast, sys
with open('runner.py') as f:
    src = f.read()
for line in src.split('\n'):
    if 'schedule.every' in line and 'coffee' in line:
        print(line.strip())
"
```

Expected: コーヒータスク4行が出力される

- [ ] **Step 3: 全テストを最終確認する**

```bash
cd ~/ai-org && python3 -m pytest tests/ -v
```

Expected: 全テスト PASS
