# ワイン記憶ハブ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Obsidian保管庫を共通の台帳にして、ai-org がワインの動画・投稿テーマの「似たもの」を避け、コーヒーの自動実行を止める。

**Architecture:** 新規モジュール `vault.py`（台帳の読み書きと類似判定）を `tools_video.fetch_broll` と `runner.run_agent` から呼ぶ。保管庫の作成と初期登録は `scripts/` の冪等スクリプトで行う。保管庫は環境変数 `WINE_VAULT_PATH` で指定し、未設定・書き込み不可のときは従来どおり動く（例外を出さない）。

**Tech Stack:** Python 3、pytest、既存の `schedule` / `requests`。新規依存なし。

**Spec:** `docs/superpowers/specs/2026-11-04-wine-memory-hub-design.md`

## Global Constraints

- 保管庫は ai-org リポジトリの外（既定 `~/Documents/ワイン台帳`）。保管庫の中身をコミットしない。
- ai-org は Public リポジトリ。台帳・コード・テストに秘密情報（キー、パスワード）を入れない。`~/Desktop/CHIAVE` は索引に入れない。
- 既存の B-roll 重複防止（`output/.broll_used.json` の ID/md5）は残す。
- コーヒーのコード・エージェント・過去の出力は削除しない。止めるのは自動実行の登録だけ。
- 有料API（Higgsfield など）の動作は変更しない。
- 台帳の1行の形式：`名称｜種類｜切り口(一言)｜作成日｜場所(パスまたはURL)｜使用状況`（B-roll.md のみ `取得日｜キーワード｜映像の説明語｜Pexels動画ID｜保存先`）。
- 追記専用ファイル（B-roll.md、投稿テーマ.md）は ai-org が追記のみ行い、人が手で編集するファイルと分ける。

## Review Focus

1. `WINE_VAULT_PATH` が未設定、存在しない、書き込み不可 → 例外を出さず従来動作（台帳なし）で続く。
2. Pexels の動画に `url` が無い、または説明語が1語も取れない → 類似判定をスキップして従来どおり取得する。
3. 台帳ファイルに壊れた行・空行・日本語が混在 → 読み飛ばして続き、追記は壊さない。
4. 同じ週の同じ実行で連続して取る B-roll 同士が似ている → 直前に追記した行も判定に使う。
5. 空フォルダ・ドットファイル（`.DS_Store`）だらけの保存フォルダ → 初期登録が「空」と記録し、ファイル数に数えない。

---

### Task 1: 台帳モジュール `vault.py`

**Files:**
- Create: `vault.py`
- Test: `tests/test_vault.py`

**Interfaces:**
- Produces:
  - `vault_path() -> Optional[str]`：環境変数 `WINE_VAULT_PATH` が存在するディレクトリを指すときそのパス、それ以外は `None`。
  - `append_row(vault: Optional[str], ledger_file: str, cols: list[str]) -> bool`：`01_台帳/<ledger_file>` に `｜` 区切り1行を追記。保管庫が `None`・書き込み失敗なら `False`（例外を出さない）。`｜` と改行は `cols` の中で半角スペースに置換する。
  - `read_rows(vault: Optional[str], ledger_file: str, limit: int = 10) -> list[list[str]]`：末尾から `limit` 行の列リスト。保管庫なし・ファイルなし・ヘッダ行（`#` 始まり、`---`）・空行・列数が合わない壊れた行は除く。
  - `slug_words(video_url: str) -> set[str]`：Pexels の動画URL（例 `https://www.pexels.com/video/woman-pouring-red-wine-3195394/`）から数字だけの語とストップワード（`a the of in on with and`）を除いた小文字の語集合。取れなければ空集合。
  - `is_similar(words: set[str], recent: list[set[str]], threshold: float = 0.5) -> bool`：`words` が空なら `False`。`recent` のどれかと Jaccard 係数が `threshold` 以上なら `True`。
  - `recent_broll_words(vault: Optional[str], limit: int = 30) -> list[set[str]]`：`B-roll.md` の直近 `limit` 行の「映像の説明語」列（空白区切り）を語集合にして返す。
  - `ledger_summary(vault: Optional[str], limit: int = 10) -> str`：`投稿テーマ.md` の直近 `limit` 行を1行ずつ `・名称（切り口）` に整形。無ければ空文字。

- [ ] **Step 1: Write the failing tests** in `tests/test_vault.py`
  - `test_vault_path_requires_existing_dir`：未設定で `None`／存在しないパスで `None`／存在するディレクトリでそのパス（`monkeypatch.setenv`）。
  - `test_append_row_and_read_rows_roundtrip`：`append_row(tmp, "投稿テーマ.md", ["A","テーマ","切り口","2026-11-04","x","使用済"])` が `True`、`read_rows` が `[["A","テーマ","切り口","2026-11-04","x","使用済"]]` を返す。`01_台帳/` が無くても作られる。
  - `test_append_row_replaces_separator_and_newline`：`cols` に `｜` と `\n` を含めても1行・6列のまま読み戻せる。
  - `test_append_row_returns_false_without_vault`：`vault=None` で `False`、例外なし。
  - `test_read_rows_skips_broken_lines`：ヘッダ行、空行、列が足りない行を含むファイルで正しい行だけ返る。
  - `test_slug_words`：上記URLが `{"woman","pouring","red","wine"}`。`slug_words("")` と `slug_words("https://www.pexels.com/video/3195394/")` は空集合。
  - `test_is_similar`：`{"red","wine","glass"}` と `{"red","wine","pouring"}`（Jaccard 0.5）が `True`、`{"vineyard","sunset"}` と前者が `False`、空集合は常に `False`。
  - `test_ledger_summary_formats_recent_rows`：3行追記して `limit=2` で末尾2行が `・名称（切り口）` で返る。

- [ ] **Step 2: Run** `python3 -m pytest tests/test_vault.py -v` → Expected: FAIL（`ModuleNotFoundError: vault`）。
- [ ] **Step 3: Implement `vault.py`**（上の Interfaces どおり。追記は `open(..., "a", encoding="utf-8")` に1回の `write`。ファイルが無いときは先頭にヘッダコメント行 `# <ledger_file>` を書く）。
- [ ] **Step 4: Run** `python3 -m pytest tests/test_vault.py -v` → Expected: PASS。
- [ ] **Step 5: Commit** `git add vault.py tests/test_vault.py && git commit -m "feat: 台帳モジュールvault.pyを追加"`

### Task 2: B-roll の類似回避と台帳への記録 【保留：2026-11-04 B-roll・動画素材生成を停止したため。再開時に実施】

**Files:**
- Modify: `tools_video.py`（`fetch_broll`、394行付近）
- Test: `tests/test_tools_video.py`

**Interfaces:**
- Consumes: `vault.vault_path`, `vault.slug_words`, `vault.is_similar`, `vault.recent_broll_words`, `vault.append_row`（Task 1）。
- Produces: `fetch_broll` のシグネチャは変更なし。保管庫があるとき、取得したクリップごとに `B-roll.md` へ `[取得日, キーワード, 映像の説明語（空白区切り）, Pexels動画ID, 保存先]` を追記する。

- [ ] **Step 1: Write the failing tests**（既存の `test_fetch_broll_saves_mp4` のモック方法に合わせる）
  - `test_fetch_broll_skips_similar_clip_and_takes_next`：`WINE_VAULT_PATH` を tmp にし、`B-roll.md` に説明語 `red wine glass` の行を入れる。Pexels のレスポンスは動画2本（1本目の `url` が `.../video/red-wine-glass-table-111/`、2本目が `.../video/vineyard-sunset-222/`）。保存されるのは2本目（`B-roll.md` の最終行の動画IDが `222`）。
  - `test_fetch_broll_records_ledger_row`：保存後に `B-roll.md` に1行増え、キーワードと動画IDが入っている。
  - `test_fetch_broll_works_without_vault`：`WINE_VAULT_PATH` 未設定で従来どおり保存される（既存テストがそのまま通る）。
  - `test_fetch_broll_video_without_url_field`：`url` キーの無い動画でも保存される（類似判定をスキップ）。
  - `test_fetch_broll_avoids_clip_similar_to_one_saved_moments_ago`：同じ保管庫で連続2回（`clip_index` 1 と 2）呼び、2回目は1回目と説明語が近い候補を避ける。

- [ ] **Step 2: Run** `python3 -m pytest tests/test_tools_video.py -k broll -v` → Expected: 新規テストが FAIL。
- [ ] **Step 3: Modify `fetch_broll`**：ループの先頭で `vault = vault_path()`、`recent = recent_broll_words(vault)` を一度だけ取得。各 `video` で `words = slug_words(video.get("url", ""))` を作り、`is_similar(words, recent)` なら `continue`（ダウンロードしない）。保存に成功した直後に `append_row(vault, "B-roll.md", [...])` を呼び、`recent.append(words)` で同一実行内の判定にも反映する。既存の ID/md5 判定はそのまま。
- [ ] **Step 4: Run** `python3 -m pytest tests/test_tools_video.py -v` → Expected: 全件 PASS。
- [ ] **Step 5: Commit** `git add tools_video.py tests/test_tools_video.py && git commit -m "feat: B-rollの類似回避と台帳記録を追加"`

### Task 3: 週次エージェントの事前確認と事後記録

**Files:**
- Modify: `runner.py`（`run_agent` 117行付近の【重複回避】ブロックと、`extract_theme` を呼ぶ206行付近）
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `vault.vault_path`, `vault.ledger_summary`, `vault.append_row`。
- Produces: `run_agent` のシグネチャは変更なし。カテゴリが「ワイン」で保管庫があるとき、プロンプトに `【台帳】保管庫に記録済みの直近のテーマです。切り口が近いものを避けてください:\n<ledger_summary>` を追加する。生成が完了し `theme` が取れたとき `投稿テーマ.md` に `[label, "週次", theme, 今日の日付, "Notion", "要確認"]` を追記する。

- [ ] **Step 1: Write the failing tests**
  - `test_run_agent_adds_ledger_summary_for_wine`：保管庫に2行あるとき、`messages` の最初の user 内容に `【台帳】` と2行の名称が含まれる（既存の `_stream_cm` モックで検証）。
  - `test_run_agent_no_ledger_for_coffee_or_without_vault`：保管庫未設定のときプロンプトに `【台帳】` が入らない。
  - `test_run_agent_appends_theme_to_ledger`：完了後に `投稿テーマ.md` へ1行増える。
- [ ] **Step 2: Run** `python3 -m pytest tests/test_runner.py -k ledger -v` → Expected: FAIL。
- [ ] **Step 3: Modify `run_agent`**：【重複回避】の直後（`resume_page_id` が空のときのみ）に台帳要約を追加。テーマ抽出の直後に `append_row`。どちらも保管庫なしなら何もしない。
- [ ] **Step 4: Run** `python3 -m pytest tests/ -q` → Expected: 全件 PASS。
- [ ] **Step 5: Commit** `git add runner.py tests/test_runner.py && git commit -m "feat: 週次エージェントが台帳を参照・記録する"`

### Task 4: コーヒーと動画素材生成の自動実行を止める 【実装済み：`register_schedules(coffee_enabled, video_enabled)`、環境変数 COFFEE_ENABLED / VIDEO_ENABLED（未設定＝停止）】

**Files:**
- Modify: `runner.py`（`main`、594行付近）、`CLAUDE.md`（週次スケジュール表）
- Test: `tests/test_runner.py`

**Interfaces:**
- Produces: `register_schedules(coffee_enabled: bool = False) -> None`（`runner.py`）：既存の `schedule.every()...do(...)` をすべてここへ移し、`coffee_` で始まる関数の登録は `coffee_enabled` が `True` のときだけ行う。`main()` は `register_schedules(os.environ.get("COFFEE_ENABLED") == "1")` を呼ぶ。起動時の `print` からコーヒーの行を、無効のとき外す。

- [ ] **Step 1: Write the failing tests**
  - `test_register_schedules_skips_coffee_by_default`：`schedule.clear()` 後に `register_schedules()` を呼ぶと、`schedule.get_jobs()` の `job.job_func.func.__name__` に `coffee_` で始まるものが0件、ワインのジョブ（`monday_task` 等）が存在する。
  - `test_register_schedules_registers_coffee_when_enabled`：`register_schedules(coffee_enabled=True)` で6件以上の `coffee_` ジョブ（`coffee_monday_task`, `coffee_regional_task`, `coffee_tuesday_task`, `coffee_friday_task`, `coffee_tuesday_video_task`, `coffee_tuesday_express_task`, `coffee_tuesday_note_task`）。
- [ ] **Step 2: Run** `python3 -m pytest tests/test_runner.py -k register_schedules -v` → Expected: FAIL。
- [ ] **Step 3: Implement `register_schedules` と `main` の差し替え**。`CLAUDE.md` の表のコーヒー行に「停止中（AI会社へ移行。再開は `COFFEE_ENABLED=1`）」を明記し、環境変数欄に `WINE_VAULT_PATH`、`COFFEE_ENABLED` を追記。
- [ ] **Step 4: Run** `python3 -m pytest tests/ -q` → Expected: 全件 PASS。
- [ ] **Step 5: Commit** `git add runner.py tests/test_runner.py CLAUDE.md && git commit -m "feat: コーヒーの自動実行を停止(COFFEE_ENABLEDで再開可)"`

### Task 5: 保管庫の作成スクリプト

**Files:**
- Create: `scripts/init_wine_vault.py`
- Test: `tests/test_init_wine_vault.py`

**Interfaces:**
- Produces: `init_vault(path: str) -> list[str]`：保管庫のフォルダとファイルを作り、新規に作ったパスの一覧を返す。既存ファイルは上書きしない（冪等）。作るもの：`00_ルール.md`、`01_台帳/{シリーズ,講座の回,州別,投稿テーマ,配布物,B-roll}.md`（ヘッダ行のみ）、`02_進行中.md`、`03_決めごと.md`、`04_プロモーション/`。CLI は `python3 scripts/init_wine_vault.py [パス]`（既定 `~/Documents/ワイン台帳`）。
- `00_ルール.md` の内容：作る前に `01_台帳/` と `02_進行中.md` を確認／着手時に `02_進行中.md` へ宣言／完了時に `01_台帳/` へ1行追記／`B-roll.md`・`投稿テーマ.md` は ai-org の追記専用で手で編集しない／パスワード・キーを書かない／台帳の1行の形式。`03_決めごと.md` の初期内容：企画名「イタリアワイン、迷わない私になる」8日間プロジェクト、講座は案B（4週間グループ講座・週1回60分Zoom・全4回・録画あり・LINEオープンチャット、価格14,800円・定員15名は仮置き）、コーヒーは AI会社 に一本化。

- [ ] **Step 1: Write the failing tests**
  - `test_init_vault_creates_structure`：戻り値と実ファイルが仕様の構成と一致。
  - `test_init_vault_is_idempotent_and_keeps_edits`：1回目の後に `03_決めごと.md` を書き換え、2回目の `init_vault` が空リストを返し内容が保たれる。
  - `test_rules_mention_required_steps`：`00_ルール.md` に「02_進行中」「01_台帳」「追記専用」「パスワード」の語が含まれる。
- [ ] **Step 2: Run** → Expected: FAIL。
- [ ] **Step 3: Implement**。
- [ ] **Step 4: Run** `python3 -m pytest tests/test_init_wine_vault.py -v` → Expected: PASS。
- [ ] **Step 5: Commit** `git add scripts/init_wine_vault.py tests/test_init_wine_vault.py && git commit -m "feat: ワイン保管庫の作成スクリプトを追加"`

### Task 6: 初期登録スクリプト（デスクトップ保存フォルダ→台帳）

**Files:**
- Create: `scripts/backfill_wine_vault.py`
- Test: `tests/test_backfill_wine_vault.py`

**Interfaces:**
- Consumes: `vault.append_row`（Task 1）。
- Produces: `backfill(archive: str, vault: str) -> dict[str, int]`：`archive`（既定 `~/Desktop/投稿内容・資料一式保存用フォルダー`）直下とその下を次の規則で分類し、台帳へ追記して `{"講座の回": n, "州別": n, "シリーズ": n, "配布物": n, "空": n}` を返す。
  - 直下で名前が `数字＋・` または `数字＋空白` で始まるフォルダ → `講座の回.md`（種類「講座の回」）。
  - `20州の旅` を含む名前のフォルダの直下の子フォルダ → `州別.md`（種類「州」、列「切り口」にファイル数）。
  - `リール素材` の直下の子フォルダ → `シリーズ.md`（種類「リール」）。
  - `trivia`、`ワイン診断`、`AISテイスティング方` → `シリーズ.md`（種類「カルーセル/資料」）。
  - `公式LINE登録者プレゼント`、`資料作成用アセット` → `配布物.md`。
  - ファイル数は `.DS_Store` と隠しファイルを除いて数える。0件のフォルダは「使用状況」に `空` と書く（どの台帳にも入れず、`空` に数える）。
  - 場所の列は絶対パス。2回実行しても同じ名称を重複追記しない（名称＋場所で判定）。
  - `CHIAVE` を含むパスは決して読まない。

- [ ] **Step 1: Write the failing tests**（`tmp_path` に疑似ツリーを作る）
  - `test_classifies_lessons_states_series_and_gifts`：各分類に正しい件数。
  - `test_empty_folder_marked_and_not_counted_as_file`：`.DS_Store` だけのフォルダが `空`。
  - `test_backfill_is_idempotent`：2回目は追記0件、台帳の行数が変わらない。
  - `test_never_reads_chiave`：`CHIAVE` フォルダを `archive` 直下に置いても台帳に一切出ない。
- [ ] **Step 2: Run** → Expected: FAIL。
- [ ] **Step 3: Implement**（CLI は `--archive` と `--vault`。実行前に件数の予定を表示する `--dry-run` を付ける）。
- [ ] **Step 4: Run** `python3 -m pytest tests/ -q` → Expected: 全件 PASS。
- [ ] **Step 5: Commit** `git add scripts/backfill_wine_vault.py tests/test_backfill_wine_vault.py && git commit -m "feat: 保存フォルダを台帳へ初期登録するスクリプトを追加"`

### Task 7: 実機セットアップと動作確認（実装者が実行・ユーザー操作を含む）

**Files:** なし（`.env` は Git 管理外）。

- [ ] **Step 1:** `python3 scripts/init_wine_vault.py` を実行し、`~/Documents/ワイン台帳` ができたことを確認。
- [ ] **Step 2:** `python3 scripts/backfill_wine_vault.py --dry-run` の件数を確認してから、`--dry-run` なしで実行。`01_台帳/` の各ファイルを開き、行数がおおよそ「講座の回 約10、州別 約20、シリーズ 約20、配布物 数件」であることを確認。**判断に迷う分類は、ユーザーに見せて直してもらう。**
- [ ] **Step 3:** `.env` に `WINE_VAULT_PATH=/Users/kubotahironori/Documents/ワイン台帳` を追記（`COFFEE_ENABLED` は書かない＝停止のまま）。
- [ ] **Step 4:** `python3 -m pytest tests/ -q` が全件通ること、`python3 -c "import runner; runner.register_schedules(); import schedule; print(sorted({j.job_func.func.__name__ for j in schedule.get_jobs()}))"` の出力にコーヒーのジョブが無いことを確認。
- [ ] **Step 5（ユーザー操作）:** Obsidian で「保管庫を開く」から `~/Documents/ワイン台帳` を選ぶ。Claude アプリのマーケティングのプロジェクトに、この保管庫フォルダへのアクセスを許可し、プロジェクトの指示に「作業前に `00_ルール.md` を読む」を書く。
- [ ] **Step 6:** 稼働中の `runner.py`（LaunchAgent）を再起動して、新しい設定を反映する。

## 自己レビュー（計画 vs 設計書）

- 保管庫の構成（4.1）→ Task 5。初期登録（4.2）→ Task 6、Task 7。B-roll（4.3-1）→ Task 2。事前確認・事後記録（4.3-2,3）→ Task 3。コーヒー停止（4.3-4）→ Task 4。環境変数と失敗時の継続（4.3-5）→ Task 1 のテストと Review Focus。Claude アプリ側（4.3）→ Task 5 のルール内容と Task 7 Step 5。
- 型・関数名は Task 1 の Interfaces で定義したものを以降のタスクが同名で使用（`vault_path`, `append_row`, `read_rows`, `slug_words`, `is_similar`, `recent_broll_words`, `ledger_summary`）。
- ノンゴール（デスクトップのファイルを動かさない、`AI会社` を触らない、コーヒーのコードを消さない）に反するタスクはない。
