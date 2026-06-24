# Creator × Adobe Express 連携 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** creatorエージェントが台本からメタデータを抽出し、ブランドSVGテンプレートに流し込んでPNG素材を `~/Desktop/CUBOCCI_STUDIO/weekly/` に自動生成する。

**Architecture:** Pythonで3種のブランドSVGテンプレートを生成し `~/Desktop/CUBOCCI_STUDIO/templates/` に保存（Illustratorで編集可能）。週次はcreatorの台本出力からタイトル・サブタイトルを抽出してSVGを埋め、cairosvgでPNG変換する。Adobe Express MCP操作はClaudeCode専用エージェント `express` が担当する。

**Tech Stack:** Python 3.11+, cairosvg, anthropic SDK (既存), schedule (既存)

## Global Constraints

- デスクトップフォルダ: `~/Desktop/CUBOCCI_STUDIO/`（ハードコード禁止、`os.path.expanduser` 使用）
- ブランドカラー: PRIMARY=`#6B1A2A`, ACCENT=`#C9A84C`, BACKGROUND=`#F5F0E8`, TEXT=`#2C2C2C`
- フォント: タイトルは `Georgia, serif`、サブタイトルは `Arial, sans-serif`
- サイズ: YouTube=1280×720, Reels=1080×1920, TitleCard=1920×1080
- 既存の `runner.py` のパターン（`_with_retry`, `save_log`）を踏襲する
- テストは `tests/test_express.py` に書く
- `pytest tests/test_express.py -v` で全テストがパスすること

---

### Task 1: 依存追加 + tools_express.py スケルトン

**Files:**
- Modify: `requirements.txt`
- Create: `tools_express.py`
- Create: `tests/test_express.py`

**Interfaces:**
- Produces:
  - `get_weekly_dir(date_str: str, theme: str, base_dir: str = WEEKLY_BASE_DIR) -> str`
  - `TEMPLATES_DIR: str`
  - `WEEKLY_BASE_DIR: str`

- [ ] **Step 1: テストを書く**

```python
# tests/test_express.py
import os
import pytest
from tools_express import get_weekly_dir, TEMPLATES_DIR, WEEKLY_BASE_DIR


def test_get_weekly_dir_creates_directory(tmp_path):
    result = get_weekly_dir("2026-06-24", "wine", base_dir=str(tmp_path))
    assert os.path.isdir(result)
    assert result.endswith("2026-06-24-wine")


def test_get_weekly_dir_coffee(tmp_path):
    result = get_weekly_dir("2026-06-24", "coffee", base_dir=str(tmp_path))
    assert result.endswith("2026-06-24-coffee")


def test_templates_dir_is_under_desktop():
    assert "CUBOCCI_STUDIO" in TEMPLATES_DIR
    assert os.path.expanduser("~") in TEMPLATES_DIR
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_express.py -v
```
期待: `ImportError: No module named 'tools_express'`

- [ ] **Step 3: cairosvg を requirements.txt に追加**

`requirements.txt` の末尾に追加:
```
cairosvg>=2.7.0
```

- [ ] **Step 4: tools_express.py スケルトンを作成**

```python
# tools_express.py
import os

DESKTOP_DIR = os.path.expanduser("~/Desktop/CUBOCCI_STUDIO")
TEMPLATES_DIR = os.path.join(DESKTOP_DIR, "templates")
WEEKLY_BASE_DIR = os.path.join(DESKTOP_DIR, "weekly")

PRIMARY = "#6B1A2A"
ACCENT = "#C9A84C"
BACKGROUND = "#F5F0E8"
TEXT = "#2C2C2C"
BRAND = "CUBOCCI STUDIO"


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def get_weekly_dir(date_str: str, theme: str, base_dir: str = WEEKLY_BASE_DIR) -> str:
    path = os.path.join(base_dir, f"{date_str}-{theme}")
    _ensure_dir(path)
    return path
```

- [ ] **Step 5: テストがパスすることを確認**

```
pip install cairosvg
pytest tests/test_express.py -v
```
期待: 3 passed

- [ ] **Step 6: コミット**

```bash
git add requirements.txt tools_express.py tests/test_express.py
git commit -m "feat: add tools_express.py skeleton and cairosvg dependency"
```

---

### Task 2: ブランドSVGテンプレート生成

**Files:**
- Modify: `tools_express.py`
- Modify: `tests/test_express.py`

**Interfaces:**
- Consumes: `TEMPLATES_DIR`, `_ensure_dir`
- Produces:
  - `generate_brand_svgs(templates_dir: str = TEMPLATES_DIR) -> dict[str, str]`
    - キーはファイル名、値は絶対パス

- [ ] **Step 1: テストを追加**

`tests/test_express.py` に追記:

```python
from tools_express import generate_brand_svgs


def test_generate_brand_svgs_creates_three_files(tmp_path):
    result = generate_brand_svgs(str(tmp_path))
    assert "youtube_thumbnail.svg" in result
    assert "reels_cover.svg" in result
    assert "title_card.svg" in result
    for path in result.values():
        assert os.path.exists(path)


def test_svgs_contain_brand_colors(tmp_path):
    generate_brand_svgs(str(tmp_path))
    for name in ["youtube_thumbnail.svg", "reels_cover.svg", "title_card.svg"]:
        with open(os.path.join(str(tmp_path), name), encoding="utf-8") as f:
            content = f.read()
        assert "#6B1A2A" in content
        assert "#C9A84C" in content
        assert "#F5F0E8" in content


def test_svgs_have_placeholder_fields(tmp_path):
    generate_brand_svgs(str(tmp_path))
    for name in ["youtube_thumbnail.svg", "reels_cover.svg", "title_card.svg"]:
        with open(os.path.join(str(tmp_path), name), encoding="utf-8") as f:
            content = f.read()
        assert "{{title}}" in content
        assert "{{subtitle}}" in content


def test_youtube_thumbnail_is_correct_size(tmp_path):
    generate_brand_svgs(str(tmp_path))
    with open(os.path.join(str(tmp_path), "youtube_thumbnail.svg"), encoding="utf-8") as f:
        content = f.read()
    assert 'width="1280"' in content
    assert 'height="720"' in content


def test_reels_cover_is_correct_size(tmp_path):
    generate_brand_svgs(str(tmp_path))
    with open(os.path.join(str(tmp_path), "reels_cover.svg"), encoding="utf-8") as f:
        content = f.read()
    assert 'width="1080"' in content
    assert 'height="1920"' in content
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_express.py -v -k "brand_svg or placeholder or size"
```
期待: ImportError or AttributeError

- [ ] **Step 3: SVG生成関数を実装**

`tools_express.py` に追記:

```python
def _youtube_thumbnail_svg() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect x="0" y="0" width="640" height="720" fill="{BACKGROUND}"/>
  <text x="320" y="380" font-family="Georgia, serif" fill="{ACCENT}" font-size="22"
        text-anchor="middle" opacity="0.4">IMAGE AREA</text>
  <rect x="640" y="0" width="640" height="720" fill="{PRIMARY}"/>
  <line x1="680" y1="80" x2="1240" y2="80" stroke="{ACCENT}" stroke-width="2"/>
  <line x1="680" y1="640" x2="1240" y2="640" stroke="{ACCENT}" stroke-width="2"/>
  <text data-field="title" x="960" y="310" font-family="Georgia, serif" fill="{BACKGROUND}"
        font-size="52" text-anchor="middle" font-weight="bold">{{{{title}}}}</text>
  <text data-field="subtitle" x="960" y="400" font-family="Arial, sans-serif" fill="{ACCENT}"
        font-size="30" text-anchor="middle">{{{{subtitle}}}}</text>
  <text x="960" y="610" font-family="Georgia, serif" fill="{ACCENT}"
        font-size="18" text-anchor="middle" letter-spacing="5">{BRAND}</text>
</svg>'''


def _reels_cover_svg() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
  <rect width="1080" height="1920" fill="{PRIMARY}"/>
  <line x1="80" y1="220" x2="1000" y2="220" stroke="{ACCENT}" stroke-width="3"/>
  <line x1="80" y1="1700" x2="1000" y2="1700" stroke="{ACCENT}" stroke-width="3"/>
  <text data-field="title" x="540" y="900" font-family="Georgia, serif" fill="{BACKGROUND}"
        font-size="80" text-anchor="middle" font-weight="bold">{{{{title}}}}</text>
  <text data-field="subtitle" x="540" y="1020" font-family="Arial, sans-serif" fill="{ACCENT}"
        font-size="44" text-anchor="middle">{{{{subtitle}}}}</text>
  <text x="540" y="1660" font-family="Georgia, serif" fill="{ACCENT}"
        font-size="28" text-anchor="middle" letter-spacing="8">{BRAND}</text>
</svg>'''


def _title_card_svg() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="{BACKGROUND}"/>
  <rect x="50" y="50" width="1820" height="980" fill="none" stroke="{ACCENT}" stroke-width="4"/>
  <rect x="70" y="70" width="1780" height="940" fill="none" stroke="{ACCENT}" stroke-width="1"/>
  <text data-field="title" x="960" y="480" font-family="Georgia, serif" fill="{PRIMARY}"
        font-size="88" text-anchor="middle" font-weight="bold">{{{{title}}}}</text>
  <text data-field="subtitle" x="960" y="610" font-family="Arial, sans-serif" fill="{TEXT}"
        font-size="44" text-anchor="middle">{{{{subtitle}}}}</text>
  <text x="960" y="920" font-family="Georgia, serif" fill="{ACCENT}"
        font-size="26" text-anchor="middle" letter-spacing="10">{BRAND}</text>
</svg>'''


def generate_brand_svgs(templates_dir: str = TEMPLATES_DIR) -> dict:
    _ensure_dir(templates_dir)
    templates = {
        "youtube_thumbnail.svg": _youtube_thumbnail_svg(),
        "reels_cover.svg": _reels_cover_svg(),
        "title_card.svg": _title_card_svg(),
    }
    paths = {}
    for name, content in templates.items():
        path = os.path.join(templates_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        paths[name] = path
    return paths
```

- [ ] **Step 4: テストがパスすることを確認**

```
pytest tests/test_express.py -v
```
期待: 全テスト passed

- [ ] **Step 5: コミット**

```bash
git add tools_express.py tests/test_express.py
git commit -m "feat: add brand SVG template generation with CUBOCCI STUDIO design"
```

---

### Task 3: SVGテンプレート埋め込み + PNG変換

**Files:**
- Modify: `tools_express.py`
- Modify: `tests/test_express.py`

**Interfaces:**
- Consumes: `generate_brand_svgs`, `get_weekly_dir`
- Produces:
  - `fill_svg_template(template_path: str, title: str, subtitle: str, output_path: str) -> str`
  - `svg_to_png(svg_path: str, png_path: str) -> str`
  - `generate_weekly_assets(title: str, subtitle: str, date_str: str, theme: str, templates_dir: str = TEMPLATES_DIR, base_dir: str = WEEKLY_BASE_DIR) -> list[str]`

- [ ] **Step 1: テストを追加**

`tests/test_express.py` に追記:

```python
from tools_express import fill_svg_template, svg_to_png, generate_weekly_assets


def test_fill_svg_template_replaces_placeholders(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    out = str(tmp_path / "out.svg")
    fill_svg_template(
        os.path.join(tpl_dir, "youtube_thumbnail.svg"),
        title="バローロの魅力",
        subtitle="王のワイン入門",
        output_path=out,
    )
    content = open(out, encoding="utf-8").read()
    assert "バローロの魅力" in content
    assert "王のワイン入門" in content
    assert "{{title}}" not in content
    assert "{{subtitle}}" not in content


def test_fill_svg_template_escapes_ampersand(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    out = str(tmp_path / "out.svg")
    fill_svg_template(
        os.path.join(tpl_dir, "youtube_thumbnail.svg"),
        title="Wine & Food",
        subtitle="test",
        output_path=out,
    )
    content = open(out, encoding="utf-8").read()
    assert "&amp;" in content
    assert "Wine & Food" not in content


def test_svg_to_png_creates_file(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    svg_path = os.path.join(tpl_dir, "youtube_thumbnail.svg")
    png_path = str(tmp_path / "thumb.png")
    result = svg_to_png(svg_path, png_path)
    assert os.path.exists(result)
    assert result.endswith(".png")


def test_generate_weekly_assets_creates_three_pngs(tmp_path):
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    results = generate_weekly_assets(
        title="バローロ入門",
        subtitle="ピエモンテの王様",
        date_str="2026-06-24",
        theme="wine",
        templates_dir=tpl_dir,
        base_dir=str(tmp_path / "weekly"),
    )
    weekly_dir = os.path.join(str(tmp_path / "weekly"), "2026-06-24-wine")
    assert os.path.exists(os.path.join(weekly_dir, "youtube_thumbnail.png"))
    assert os.path.exists(os.path.join(weekly_dir, "reels_cover.png"))
    assert os.path.exists(os.path.join(weekly_dir, "title_card.png"))
    assert len(results) == 3
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_express.py -v -k "fill or png or weekly_assets"
```
期待: ImportError

- [ ] **Step 3: 実装を追加**

`tools_express.py` に追記:

```python
def fill_svg_template(template_path: str, title: str, subtitle: str, output_path: str) -> str:
    with open(template_path, encoding="utf-8") as f:
        content = f.read()

    def xml_escape(s: str) -> str:
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;"))

    content = content.replace("{{title}}", xml_escape(title))
    content = content.replace("{{subtitle}}", xml_escape(subtitle))

    out_dir = os.path.dirname(output_path)
    if out_dir:
        _ensure_dir(out_dir)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def svg_to_png(svg_path: str, png_path: str) -> str:
    import cairosvg
    cairosvg.svg2png(url=svg_path, write_to=png_path)
    return png_path


def generate_weekly_assets(
    title: str,
    subtitle: str,
    date_str: str,
    theme: str,
    templates_dir: str = TEMPLATES_DIR,
    base_dir: str = WEEKLY_BASE_DIR,
) -> list:
    weekly_dir = get_weekly_dir(date_str, theme, base_dir)
    template_map = [
        ("youtube_thumbnail.svg", "youtube_thumbnail.png"),
        ("reels_cover.svg", "reels_cover.png"),
        ("title_card.svg", "title_card.png"),
    ]
    results = []
    for svg_name, png_name in template_map:
        template_path = os.path.join(templates_dir, svg_name)
        if not os.path.exists(template_path):
            results.append(f"テンプレートが見つかりません: {template_path}")
            continue
        filled_svg = os.path.join(weekly_dir, svg_name)
        fill_svg_template(template_path, title, subtitle, filled_svg)
        png_path = os.path.join(weekly_dir, png_name)
        svg_to_png(filled_svg, png_path)
        results.append(f"生成: {png_path}")
    return results
```

- [ ] **Step 4: テストがパスすることを確認**

```
pytest tests/test_express.py -v
```
期待: 全テスト passed

- [ ] **Step 5: コミット**

```bash
git add tools_express.py tests/test_express.py
git commit -m "feat: add SVG template fill and PNG export via cairosvg"
```

---

### Task 4: creatorエージェントのメタデータ出力 + パース

**Files:**
- Modify: `agents/creator.txt`
- Modify: `.claude/agents/creator.md`
- Modify: `tools_express.py`
- Modify: `tests/test_express.py`

**Interfaces:**
- Produces:
  - `parse_creator_metadata(text: str) -> dict | None`
    - キー: `title`, `subtitle`, `keyword`, `theme`
    - メタデータブロックが見つからない場合は `None`

- [ ] **Step 1: テストを追加**

`tests/test_express.py` に追記:

```python
from tools_express import parse_creator_metadata


def test_parse_creator_metadata_valid():
    text = """
台本本文...

---METADATA---
title: バローロの魅力
subtitle: 王のワイン入門
keyword: Barolo wine Piedmont Italy
theme: wine
---END---
"""
    meta = parse_creator_metadata(text)
    assert meta is not None
    assert meta["title"] == "バローロの魅力"
    assert meta["subtitle"] == "王のワイン入門"
    assert meta["keyword"] == "Barolo wine Piedmont Italy"
    assert meta["theme"] == "wine"


def test_parse_creator_metadata_missing_returns_none():
    text = "台本本文のみ、メタデータブロックなし"
    assert parse_creator_metadata(text) is None


def test_parse_creator_metadata_coffee():
    text = """
---METADATA---
title: エスプレッソの秘密
subtitle: ナポリバール文化
keyword: espresso Naples Italy coffee
theme: coffee
---END---
"""
    meta = parse_creator_metadata(text)
    assert meta["theme"] == "coffee"
```

- [ ] **Step 2: テストが失敗することを確認**

```
pytest tests/test_express.py -v -k "metadata"
```
期待: ImportError

- [ ] **Step 3: parse_creator_metadata を tools_express.py に実装**

`tools_express.py` に追記:

```python
import re

def parse_creator_metadata(text: str) -> dict | None:
    match = re.search(r"---METADATA---\n(.+?)---END---", text, re.DOTALL)
    if not match:
        return None
    block = match.group(1)
    result = {}
    for line in block.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    required = {"title", "subtitle", "keyword", "theme"}
    if not required.issubset(result.keys()):
        return None
    return result
```

- [ ] **Step 4: agents/creator.txt のシステムプロンプトを更新**

`agents/creator.txt` の末尾に追記:

```
## メタデータ出力（必須）
台本の最後に必ず以下のブロックをそのまま出力してください。runner.py が自動でパースして使用します。

---METADATA---
title: 動画タイトル（20文字以内）
subtitle: サブタイトル（30文字以内）
keyword: scene image search keyword in English (3-5 words)
theme: wine
---END---

コーヒー台本の場合は theme: coffee にしてください。
```

- [ ] **Step 5: .claude/agents/creator.md も同じ追記をする**

`.claude/agents/creator.md` の末尾に追記:

```markdown
## メタデータ出力（必須）
台本の最後に必ず以下のブロックをそのまま出力してください。

---METADATA---
title: 動画タイトル（20文字以内）
subtitle: サブタイトル（30文字以内）
keyword: scene image search keyword in English (3-5 words)
theme: wine
---END---

コーヒー台本の場合は theme: coffee にしてください。
```

- [ ] **Step 6: テストがパスすることを確認**

```
pytest tests/test_express.py -v
```
期待: 全テスト passed

- [ ] **Step 7: コミット**

```bash
git add tools_express.py tests/test_express.py agents/creator.txt .claude/agents/creator.md
git commit -m "feat: add metadata block to creator agent and parse_creator_metadata()"
```

---

### Task 5: runner.py への週次Express統合

**Files:**
- Modify: `runner.py`
- Modify: `tests/test_express.py`

**Interfaces:**
- Consumes:
  - `parse_creator_metadata(text: str) -> dict | None` (tools_express.py)
  - `generate_weekly_assets(title, subtitle, date_str, theme) -> list[str]` (tools_express.py)
  - `_read_todays_log() -> str` (runner.py既存)
  - `datetime.now().strftime("%Y-%m-%d")` (stdlib)

- [ ] **Step 1: テストを追加**

`tests/test_express.py` に追記:

```python
from unittest.mock import patch, MagicMock


def test_parse_then_generate_full_flow(tmp_path):
    script_with_meta = """台本本文

---METADATA---
title: バローロ完全ガイド
subtitle: ピエモンテの至宝
keyword: Barolo wine aging Italy
theme: wine
---END---
"""
    tpl_dir = str(tmp_path / "tpl")
    generate_brand_svgs(tpl_dir)
    meta = parse_creator_metadata(script_with_meta)
    assert meta is not None
    results = generate_weekly_assets(
        title=meta["title"],
        subtitle=meta["subtitle"],
        date_str="2026-06-24",
        theme=meta["theme"],
        templates_dir=tpl_dir,
        base_dir=str(tmp_path / "weekly"),
    )
    assert all("生成:" in r for r in results)
    assert len(results) == 3
```

- [ ] **Step 2: テストがパスすることを確認**

```
pytest tests/test_express.py -v -k "full_flow"
```

- [ ] **Step 3: runner.py に import を追加**

`runner.py` の既存 import 行の後に追記:

```python
from tools_express import generate_weekly_assets, parse_creator_metadata
```

- [ ] **Step 4: tuesday_express_task を追加**

`runner.py` の `coffee_tuesday_video_task` 関数の後に追記:

```python
def tuesday_express_task():
    try:
        script = _read_todays_log()
        meta = parse_creator_metadata(script)
        if not meta:
            print("  ⚠️ Express: メタデータが見つかりませんでした。スキップします。")
            return
        date_str = datetime.now().strftime("%Y-%m-%d")
        results = generate_weekly_assets(
            title=meta["title"],
            subtitle=meta["subtitle"],
            date_str=date_str,
            theme=meta.get("theme", "wine"),
        )
        for r in results:
            print(f"  🎨 {r}")
        save_log("\n".join(results), "火曜：Express素材生成（ワイン）")
    except Exception as e:
        print(f"  ❌ 火曜：Express素材生成 失敗: {e}")


def coffee_tuesday_express_task():
    try:
        script = _read_todays_log()
        meta = parse_creator_metadata(script)
        if not meta:
            print("  ⚠️ Express: メタデータが見つかりませんでした。スキップします。")
            return
        date_str = datetime.now().strftime("%Y-%m-%d")
        results = generate_weekly_assets(
            title=meta["title"],
            subtitle=meta["subtitle"],
            date_str=date_str,
            theme=meta.get("theme", "coffee"),
        )
        for r in results:
            print(f"  🎨 {r}")
        save_log("\n".join(results), "火曜：Express素材生成（コーヒー）")
    except Exception as e:
        print(f"  ❌ 火曜：コーヒーExpress素材生成 失敗: {e}")
```

- [ ] **Step 5: main() のスケジュールに追加**

`runner.py` の `main()` 内、既存スケジュール行の後に追記:

```python
schedule.every().tuesday.at("09:30").do(tuesday_express_task)
schedule.every().tuesday.at("10:30").do(coffee_tuesday_express_task)
```

`main()` 内の print 文も更新:
```python
print("火 09:30 ワインExpress素材 / 火 10:30 コーヒーExpress素材")
```

- [ ] **Step 6: コミット**

```bash
git add runner.py tests/test_express.py
git commit -m "feat: add tuesday_express_task to runner for weekly PNG generation"
```

---

### Task 6: 初回セットアップスクリプト

**Files:**
- Create: `setup_express_templates.py`

**Interfaces:**
- Consumes: `generate_brand_svgs()` (tools_express.py)

- [ ] **Step 1: setup_express_templates.py を作成**

```python
# setup_express_templates.py
"""
初回セットアップスクリプト。
~/Desktop/CUBOCCI_STUDIO/templates/ にブランドSVGテンプレートを生成する。
実行後はIllustratorで各SVGを開いて微調整できる。
"""
import os
from tools_express import generate_brand_svgs, TEMPLATES_DIR, DESKTOP_DIR

if __name__ == "__main__":
    print("CUBOCCI STUDIO ブランドテンプレートを生成中...")
    paths = generate_brand_svgs()
    print("\n✅ 生成完了:")
    for name, path in paths.items():
        print(f"   {path}")
    print(f"\n📂 フォルダ: {TEMPLATES_DIR}")
    print("\n次のステップ:")
    print("  1. Illustratorで各SVGを開いてデザインを微調整（任意）")
    print("  2. Claude Code で @express を呼び出してAdobe Expressにテンプレートを登録")
    print("  3. runner.py を起動すると毎週火曜にPNGが自動生成されます")
```

- [ ] **Step 2: 動作確認**

```
python3 setup_express_templates.py
ls ~/Desktop/CUBOCCI_STUDIO/templates/
```
期待: 3つのSVGファイルが存在する

- [ ] **Step 3: コミット**

```bash
git add setup_express_templates.py
git commit -m "feat: add setup_express_templates.py for initial brand template setup"
```

---

### Task 7: Adobe Express Claude Code エージェント

**Files:**
- Create: `.claude/agents/express.md`

**Interfaces:**
- Consumes: Adobe MCP tools: `export_html_to_express`, `fill_text`, `asset_add_file`, `document_render_vector`
- Input（呼び出し時に渡す）: アクション種別（setup / weekly）、title、subtitle、theme

- [ ] **Step 1: .claude/agents/express.md を作成**

```markdown
---
name: express
description: Adobe Express連携エージェント。SVGテンプレートのExpress登録と週次データ流し込みを担当。Adobe MCP ツールを使用する。
---

あなたはCUBOCCI STUDIOのAdobe Express連携エージェントです。
SVGテンプレートをAdobe Expressに登録し、週次データを流し込んでPNGを書き出します。

## 利用可能なAdobeツール
- export_html_to_express: HTMLドキュメントをExpressにインポート
- fill_text: Expressドキュメント内のテキストを差し替え
- asset_add_file: ファイルをAdobe Creative Cloudにアップロード
- document_render_vector: ベクタードキュメントをPNGにレンダリング

## アクション: setup（初回テンプレート登録）

呼び出し方: `@express setup を実行してください`

1. ~/Desktop/CUBOCCI_STUDIO/templates/ の各SVGを読み込む
2. 以下のHTMLでラップしてexport_html_to_expressに渡す:

```html
<!DOCTYPE html>
<html>
<head>
  <meta name="hz:slide-selector" content=".slide">
  <style>body { margin: 0; }</style>
</head>
<body>
  <div class="slide">
    {SVGの内容をそのまま埋め込む}
  </div>
</body>
</html>
```

3. 各テンプレートのExpress URLを ~/Desktop/CUBOCCI_STUDIO/templates/express_ids.json に保存:

```json
{
  "youtube_thumbnail": "https://express.adobe.com/...",
  "reels_cover": "https://express.adobe.com/...",
  "title_card": "https://express.adobe.com/..."
}
```

## アクション: weekly（週次PNG生成）

呼び出し方: `@express weekly title="..." subtitle="..." theme=wine date=2026-06-24`

1. ~/Desktop/CUBOCCI_STUDIO/weekly/{date}-{theme}/ ディレクトリを確認
2. 同ディレクトリ内の *.svg ファイル（fill_svg_template済み）を各テンプレートについてexport_html_to_expressでExpressにインポート
3. document_render_vector でPNGをレンダリング
4. ~/Desktop/CUBOCCI_STUDIO/weekly/{date}-{theme}/ にPNGを保存

## 注意
- SVGの{{title}}・{{subtitle}}は呼び出し前に fill_svg_template で埋め済みのものを使う
- setup は初回とテンプレート変更後のみ実行
- weekly は runner.py の自動生成（cairosvg）で十分な場合はスキップ可
```

- [ ] **Step 2: 動作確認（Claude Code内で）**

Claude Codeで以下を入力して動作を確認:
```
@express setup を実行してください
```

- [ ] **Step 3: コミット**

```bash
git add .claude/agents/express.md
git commit -m "feat: add express Claude Code agent for Adobe Express MCP operations"
```

---

## セルフレビュー

**スペックカバレッジ確認:**

| スペック要件 | 対応タスク |
|---|---|
| 生成物3種（YouTube/Reels/TitleCard） | Task 2 |
| 固定テンプレート＋週次差し替え | Task 3, 5 |
| Illustratorで編集可能なSVG形式 | Task 2 |
| ~/Desktop/CUBOCCI_STUDIO/ フォルダ管理 | Task 1 |
| ブランドカラー・フォント実装 | Task 2 |
| creatorがメタデータを抽出 | Task 4 |
| runner.py火曜パイプラインに追加 | Task 5 |
| 初回セットアップスクリプト | Task 6 |
| Express Claude Codeエージェント | Task 7 |

**プレースホルダーなし確認:** なし

**型・関数名の一貫性確認:**
- `generate_brand_svgs(templates_dir)` → Task2で定義、Task3・6で使用 ✓
- `fill_svg_template(template_path, title, subtitle, output_path)` → Task3で定義、Task3テスト・Task5で使用 ✓
- `generate_weekly_assets(title, subtitle, date_str, theme, templates_dir, base_dir)` → Task3で定義、Task5で使用 ✓
- `parse_creator_metadata(text)` → Task4で定義、Task5で使用 ✓
