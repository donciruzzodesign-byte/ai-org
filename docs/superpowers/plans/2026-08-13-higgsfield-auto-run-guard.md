# Higgsfield課金APIガード（週次自動実行）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `runner.py`の週次自動実行（火曜11:00ワイン／12:00コーヒー）が、オーナーの明示的な事前許可なしにHiggsfield課金API（`generate_scene_video`）を呼ばないようにする。

**Architecture:** リポジトリ直下のフラグファイル（`.higgsfield_auto_once`）の存在有無で、その回の自動実行1回に限り`generate_scene_video`をLLMに見せる／見せないを切り替える。フラグは読み取り時に即座に削除（消費）される。オーナーは`scripts/enable_higgsfield_once.py`を事前に実行してフラグを立てる。ワイン・コーヒーは独立にフラグを消費する。

**Tech Stack:** Python（既存の`tools_video.py`／`runner.py`にロジック追加、新規スクリプト1本）、pytest + `unittest.mock`（既存パターン踏襲）

## Global Constraints

- フラグファイルパス: リポジトリ直下 `.higgsfield_auto_once`（中身は使わず存在有無のみで判定）
- フラグが存在しない場合、`run_video_agent`は`generate_scene_video`を含まないツールリストをClaude APIに渡す（デフォルトは常にこちら）
- フラグを読み取って`True`を返すのと同時に、必ずファイルを削除する（消費）。存在しない場合は`False`。ファイル操作で例外が起きた場合も`False`（フェイルセーフ、絶対に「使わせる」方向には倒れない）
- ワイン用タスクとコーヒー用タスクは、それぞれ独立に`consume_paid_video_flag()`を呼ぶ（1つのフラグで両方が有効になることはない）
- インタラクティブなClaude Codeでの`@video`エージェント利用（`.claude/agents/video.md`）はこのガードの対象外。変更しない

---

### Task 1: フラグ判定ロジックとツールリストのフィルタリング

**Files:**
- Modify: `tools_video.py:122`（`VIDEO_TOOL_DEFINITIONS`の閉じ`]`の直後、`_ensure_dir`定義の前に追加）
- Test: `tests/test_tools_video.py`（末尾に追加）

**Interfaces:**
- Produces: `HIGGSFIELD_ONESHOT_FLAG_PATH: str`（モジュール定数）
- Produces: `VIDEO_TOOL_DEFINITIONS_FREE: list`（`VIDEO_TOOL_DEFINITIONS`から`name == "generate_scene_video"`を除いたリスト）
- Produces: `consume_paid_video_flag() -> bool`
- Consumes: なし

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_tools_video.py`の末尾に追加:

```python
from tools_video import consume_paid_video_flag, VIDEO_TOOL_DEFINITIONS_FREE


def test_consume_paid_video_flag_true_and_deletes_file(tmp_path, monkeypatch):
    flag_path = str(tmp_path / ".higgsfield_auto_once")
    with open(flag_path, "w", encoding="utf-8") as f:
        f.write("")
    monkeypatch.setattr("tools_video.HIGGSFIELD_ONESHOT_FLAG_PATH", flag_path)

    result = consume_paid_video_flag()

    assert result is True
    assert not os.path.exists(flag_path)


def test_consume_paid_video_flag_false_when_absent(tmp_path, monkeypatch):
    flag_path = str(tmp_path / ".higgsfield_auto_once")
    monkeypatch.setattr("tools_video.HIGGSFIELD_ONESHOT_FLAG_PATH", flag_path)

    result = consume_paid_video_flag()

    assert result is False


def test_consume_paid_video_flag_second_call_is_false(tmp_path, monkeypatch):
    flag_path = str(tmp_path / ".higgsfield_auto_once")
    with open(flag_path, "w", encoding="utf-8") as f:
        f.write("")
    monkeypatch.setattr("tools_video.HIGGSFIELD_ONESHOT_FLAG_PATH", flag_path)

    first = consume_paid_video_flag()
    second = consume_paid_video_flag()

    assert first is True
    assert second is False


def test_video_tool_definitions_free_excludes_generate_scene_video():
    names = [t["name"] for t in VIDEO_TOOL_DEFINITIONS_FREE]
    assert "generate_scene_video" not in names
    assert "fetch_broll" in names
    assert "generate_scene_image" in names
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m pytest tests/test_tools_video.py -k "consume_paid_video_flag or VIDEO_TOOL_DEFINITIONS_FREE" -v`
Expected: FAIL（`ImportError: cannot import name 'consume_paid_video_flag'`）

- [ ] **Step 3: 実装する**

`tools_video.py`の122行目（`VIDEO_TOOL_DEFINITIONS`を閉じる`]`）の直後、`_ensure_dir`定義の前に追加:

```python
HIGGSFIELD_ONESHOT_FLAG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".higgsfield_auto_once")

VIDEO_TOOL_DEFINITIONS_FREE = [t for t in VIDEO_TOOL_DEFINITIONS if t["name"] != "generate_scene_video"]


def consume_paid_video_flag() -> bool:
    try:
        if os.path.exists(HIGGSFIELD_ONESHOT_FLAG_PATH):
            os.remove(HIGGSFIELD_ONESHOT_FLAG_PATH)
            return True
        return False
    except OSError:
        return False
```

- [ ] **Step 4: テストを実行して通ることを確認する**

Run: `python3 -m pytest tests/test_tools_video.py -v`
Expected: PASS（既存テストを含め全件）

- [ ] **Step 5: コミット**

```bash
git add tools_video.py tests/test_tools_video.py
git commit -m "$(cat <<'EOF'
feat: Higgsfield課金APIのワンショット許可フラグ判定を追加

フラグファイルの存在有無を読み取り時に消費するconsume_paid_video_flag()と、
generate_scene_videoを除いたVIDEO_TOOL_DEFINITIONS_FREEを追加。
週次自動実行から課金APIを構造的に見えなくするための土台。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: フラグを立てる手動スクリプト

**Files:**
- Create: `scripts/enable_higgsfield_once.py`
- Test: `tests/test_higgsfield_auto_run_guard.py`（新規）

**Interfaces:**
- Consumes: `tools_video.HIGGSFIELD_ONESHOT_FLAG_PATH`（Task 1で定義）
- Produces: `scripts.enable_higgsfield_once.main() -> None`（フラグファイルを作成する）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_higgsfield_auto_run_guard.py`を新規作成:

```python
import os
import sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.enable_higgsfield_once import main


def test_main_creates_flag_file(tmp_path, monkeypatch):
    flag_path = str(tmp_path / ".higgsfield_auto_once")
    monkeypatch.setattr("scripts.enable_higgsfield_once.HIGGSFIELD_ONESHOT_FLAG_PATH", flag_path)

    main()

    assert os.path.exists(flag_path)


def test_main_overwrites_existing_flag_file(tmp_path, monkeypatch):
    flag_path = str(tmp_path / ".higgsfield_auto_once")
    with open(flag_path, "w", encoding="utf-8") as f:
        f.write("stale")
    monkeypatch.setattr("scripts.enable_higgsfield_once.HIGGSFIELD_ONESHOT_FLAG_PATH", flag_path)

    main()

    with open(flag_path, encoding="utf-8") as f:
        assert f.read() == ""
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m pytest tests/test_higgsfield_auto_run_guard.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'scripts.enable_higgsfield_once'`）

- [ ] **Step 3: スクリプトを実装する**

`scripts/enable_higgsfield_once.py`を新規作成:

```python
"""次回の週次自動動画生成（火曜11:00ワイン／12:00コーヒー）で1回だけHiggsfield AI動画生成を許可する。

使い方: リポジトリ直下で `python3 scripts/enable_higgsfield_once.py`
フラグはワイン・コーヒーで別々に消費されるため、同じ週に両方で使いたい場合は
それぞれの自動実行が始まる前にもう一度実行すること。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tools_video import HIGGSFIELD_ONESHOT_FLAG_PATH


def main() -> None:
    with open(HIGGSFIELD_ONESHOT_FLAG_PATH, "w", encoding="utf-8") as f:
        f.write("")
    print(f"✅ 次回の自動動画生成1回分だけHiggsfieldを許可しました: {HIGGSFIELD_ONESHOT_FLAG_PATH}")
    print("   ワイン・コーヒーは別々に消費されます。両方で使いたい場合はそれぞれの回の前に実行してください。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストを実行して通ることを確認する**

Run: `python3 -m pytest tests/test_higgsfield_auto_run_guard.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add scripts/enable_higgsfield_once.py tests/test_higgsfield_auto_run_guard.py
git commit -m "$(cat <<'EOF'
feat: Higgsfieldワンショット許可フラグを立てる手動スクリプトを追加

python3 scripts/enable_higgsfield_once.py で次回の自動動画生成1回分だけ
generate_scene_videoの利用を許可する。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: runner.pyへの配線

**Files:**
- Modify: `runner.py:11`（import文）
- Modify: `runner.py:319-334`（`run_video_agent`の定義とtools引数）
- Modify: `runner.py:357-364`（`tuesday_video_task`）
- Modify: `runner.py:367-374`（`coffee_tuesday_video_task`）
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `VIDEO_TOOL_DEFINITIONS_FREE`, `consume_paid_video_flag`（Task 1で定義、`tools_video`からimport）
- Produces: `run_video_agent(script_text: str, topic: str, output_dir: str, allow_paid_video: bool = False) -> str`（`allow_paid_video`引数を追加。既存呼び出し元との後方互換のためデフォルト値あり）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_runner.py`に追加（既存の`test_run_video_agent_calls_video_tools`の直後）:

```python
def test_run_video_agent_default_excludes_paid_tool(tmp_path):
    final_block = MagicMock()
    final_block.text = "完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", return_value=final_response) as mock_create, \
         patch("runner.save_log"):
        run_video_agent("台本", "イタリアワイン", str(tmp_path))

    sent_tools = mock_create.call_args[1]["tools"]
    tool_names = [t["name"] for t in sent_tools]
    assert "generate_scene_video" not in tool_names


def test_run_video_agent_allow_paid_video_includes_paid_tool(tmp_path):
    final_block = MagicMock()
    final_block.text = "完了"
    final_response = MagicMock()
    final_response.stop_reason = "end_turn"
    final_response.content = [final_block]

    with patch("runner.client.messages.create", return_value=final_response) as mock_create, \
         patch("runner.save_log"):
        run_video_agent("台本", "イタリアワイン", str(tmp_path), allow_paid_video=True)

    sent_tools = mock_create.call_args[1]["tools"]
    tool_names = [t["name"] for t in sent_tools]
    assert "generate_scene_video" in tool_names


def test_tuesday_video_task_passes_consumed_flag_to_run_video_agent():
    with patch("runner.consume_paid_video_flag", return_value=True) as mock_flag, \
         patch("runner.run_video_agent") as mock_run, \
         patch("runner._read_todays_log", return_value="台本"):
        tuesday_video_task()

    mock_flag.assert_called_once()
    assert mock_run.call_args[1]["allow_paid_video"] is True


def test_coffee_tuesday_video_task_passes_consumed_flag_to_run_video_agent():
    with patch("runner.consume_paid_video_flag", return_value=False) as mock_flag, \
         patch("runner.run_video_agent") as mock_run, \
         patch("runner._read_todays_log", return_value="台本"):
        coffee_tuesday_video_task()

    mock_flag.assert_called_once()
    assert mock_run.call_args[1]["allow_paid_video"] is False
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 -m pytest tests/test_runner.py -k "paid_video or consumed_flag" -v`
Expected: FAIL（`run_video_agent() got an unexpected keyword argument 'allow_paid_video'`、および`runner.consume_paid_video_flag`が存在しないため`AttributeError`）

- [ ] **Step 3: runner.pyを実装する**

`runner.py:11`を変更:

```python
from tools_video import VIDEO_TOOL_DEFINITIONS, VIDEO_TOOL_DEFINITIONS_FREE, execute_video_tool, consume_paid_video_flag
```

`runner.py:319-334`（`run_video_agent`の定義冒頭からClaude呼び出しまで）を以下に変更:

```python
def run_video_agent(script_text: str, topic: str, output_dir: str, allow_paid_video: bool = False) -> str:
    system = load_agent("video")
    prompt = f"出力先ディレクトリ: {output_dir}\n\nトピック: {topic}\n\n台本：\n{script_text}"
    messages = [{"role": "user", "content": prompt}]
    tools = VIDEO_TOOL_DEFINITIONS if allow_paid_video else VIDEO_TOOL_DEFINITIONS_FREE

    while True:
        response = _with_retry(
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=system,
                tools=tools,
                messages=messages,
            ),
            f"video-{topic}",
        )
```

（この後に続く`if response.stop_reason == "tool_use":`以降のブロックは変更しない）

`runner.py:357-364`の`tuesday_video_task`を以下に変更:

```python
def tuesday_video_task():
    try:
        script = _read_todays_log()
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"{date_str}-wine")
        allow_paid_video = consume_paid_video_flag()
        run_video_agent(script, "イタリアワイン", output_dir, allow_paid_video=allow_paid_video)
    except Exception as e:
        print(f"  ❌ 火曜：ワイン動画素材生成 失敗: {e}")
```

`runner.py:367-374`の`coffee_tuesday_video_task`を以下に変更:

```python
def coffee_tuesday_video_task():
    try:
        script = _read_todays_log()
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"{date_str}-coffee")
        allow_paid_video = consume_paid_video_flag()
        run_video_agent(script, "イタリアコーヒー", output_dir, allow_paid_video=allow_paid_video)
    except Exception as e:
        print(f"  ❌ 火曜：コーヒー動画素材生成 失敗: {e}")
```

- [ ] **Step 4: テストを実行して通ることを確認する**

Run: `python3 -m pytest tests/test_runner.py -v`
Expected: PASS（既存テストを含め全件。特に既存の`test_run_video_agent_calls_video_tools`は`allow_paid_video`を渡さずデフォルト`False`で呼ばれるが、使用ツール名`generate_narration`は`VIDEO_TOOL_DEFINITIONS_FREE`にも含まれるため影響なく通る）

- [ ] **Step 5: コミット**

```bash
git add runner.py tests/test_runner.py
git commit -m "$(cat <<'EOF'
feat: 週次自動動画生成にHiggsfieldワンショット許可フラグを配線

tuesday_video_task/coffee_tuesday_video_taskがそれぞれ独立にフラグを消費し、
run_video_agentへallow_paid_videoとして渡す。フラグが無ければ
generate_scene_videoを含まないツールリストがClaudeに渡され、
LLMからは課金APIが見えない状態になる。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: ドキュメント更新（.gitignore・CLAUDE.md）

**Files:**
- Modify: `.gitignore`
- Modify: `CLAUDE.md:124`（`ai_video/scene_NN.mp4`と`note_article.md`の行の間、`### 手持ち写真の利用`の前に新セクションを追加）

**Interfaces:**
- Consumes: なし（Task 1〜3で実装した機能の説明のみ）
- Produces: なし（ドキュメントのみ、後続タスクなし）

- [ ] **Step 1: `.gitignore`にフラグファイルを追加する**

`.gitignore`の末尾に追加:

```
# Higgsfieldワンショット許可フラグ（ランタイム状態、コミット対象外）
.higgsfield_auto_once
```

- [ ] **Step 2: `CLAUDE.md`にフラグの使い方を追記する**

`CLAUDE.md`の124行目（`| \`note_article.md\` | ... |`の行）の直後、126行目`### 手持ち写真の利用（任意）`の前に追加:

```markdown

### Higgsfield AI動画生成の実行制御（ワンショット許可）
週次自動実行（火曜11:00ワイン／12:00コーヒー）では、`generate_scene_video`（Higgsfield課金API）はデフォルトで無効。使う回だけ事前に以下を実行する：

```bash
python3 scripts/enable_higgsfield_once.py
```

実行すると次回の自動動画生成1回分だけ有効になり、使用後は自動的にまた無効へ戻る（ワンショット）。ワイン・コーヒーは別々に消費されるため、同じ週に両方で使いたい場合はそれぞれの回の前に実行すること。Claude Codeでの`@video`エージェント利用（インタラクティブ）はこの制限の対象外。
```

- [ ] **Step 3: 変更箇所を目視確認する**

Run: `git diff .gitignore CLAUDE.md`
Expected: 上記の追記のみが差分に含まれ、既存記述の意図しない変更がないこと

- [ ] **Step 4: コミット**

```bash
git add .gitignore CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: Higgsfieldワンショット許可フラグの使い方をCLAUDE.mdと.gitignoreに反映

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: 全体検証

**Files:**
- なし（検証のみ、コード変更なし）

**Interfaces:**
- Consumes: Task 1〜4の全成果物

- [ ] **Step 1: 全テストスイートを実行する**

Run: `python3 -m pytest tests/ -v`
Expected: PASS（全件、`test_tools_video.py`の新規4テスト、`test_higgsfield_auto_run_guard.py`の新規2テスト、`test_runner.py`の新規4テストを含む）

- [ ] **Step 2: フラグの実際の生成・消費フローをシェルで一度通しで確認する**

Run:
```bash
rm -f .higgsfield_auto_once
python3 scripts/enable_higgsfield_once.py
ls -la .higgsfield_auto_once
python3 -c "from tools_video import consume_paid_video_flag; print(consume_paid_video_flag())"
python3 -c "from tools_video import consume_paid_video_flag; print(consume_paid_video_flag())"
ls .higgsfield_auto_once 2>&1 || echo "(削除済み、想定通り)"
```
Expected: `ls -la`でフラグファイルが存在することを確認 → 1回目の`consume_paid_video_flag()`は`True` → 2回目は`False` → 最後の`ls`はファイルが無い旨のエラー（想定通り）

- [ ] **Step 3: `.gitignore`が実際に機能していることを確認する**

Run: `git status --short`
Expected: Step 2で作成・消費済みの`.higgsfield_auto_once`が（存在していたとしても）`git status`に出てこないこと。念のため `git check-ignore -v .higgsfield_auto_once` も実行し、`.gitignore`のどの行がマッチしているか確認する
