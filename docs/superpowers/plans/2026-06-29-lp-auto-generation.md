# LP自動生成システム Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `lp/content.json` からスマホ対応HTMLランディングページを自動生成し、GitHub Pages で無料公開する。

**Architecture:** `tools_lp.py` が `content.json` を読み込み、Adobe Express MCP でビジュアルアセットを生成後、完全なHTMLページを `lp/index.html` として出力する。`git push` するだけで GitHub Pages が更新される。

**Tech Stack:** Python 3.9（標準ライブラリのみ）、Adobe Express MCP（セッション内）、Google Fonts CDN、GitHub Pages

## Global Constraints

- CUBOCCI STUDIO のブランド名はLP上に一切表示しない
- カラー固定: 背景 `#F5F0E8`、本文 `#6B1A2A`、見出し/アクセント `#C9A84C`
- 外部CSSライブラリ（Bootstrap等）使用禁止 — 素のCSS/JSのみ
- Python標準ライブラリのみ — 外部パッケージ追加禁止
- スマホ（375px）基準レスポンシブ、PC最大幅720px中央寄せ
- Google Fonts CDN: `Cormorant Garamond`（見出し）+ `Noto Sans JP`（本文）
- `generate_assets()` はAdobe Express MCPが使えないCI環境では空辞書を返してスキップ

---

## File Structure

```
ai-org/
├── lp/
│   ├── content.json      # LP全テキスト・設定・LINE URL（新規作成）
│   ├── index.html        # tools_lp.py が自動生成・上書き（新規作成）
│   └── assets/           # Adobe Express生成アセット置き場（新規作成）
│       ├── hero.png
│       └── gift_cover.png
├── tools_lp.py            # generate_lp() + generate_assets() + write_lp()（新規作成）
└── tests/
    └── test_lp.py         # スキーマ + HTML生成テスト（新規作成）
```

---

### Task 1: content.json とスキーマバリデーションテスト

**Files:**
- Create: `lp/content.json`
- Create: `tests/test_lp.py`

**Interfaces:**
- Produces: `lp/content.json` — Task 2の `generate_lp()` が読み込むデータファイル

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_lp.py` を作成:

```python
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CONTENT_PATH = os.path.join(os.path.dirname(__file__), "..", "lp", "content.json")

REQUIRED_KEYS = [
    "meta", "headline", "worries", "ideals", "gift",
    "cta_text", "line_steps", "profile", "story",
    "why_free", "why_me", "qa", "postscript"
]


def load_content():
    with open(CONTENT_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_content_json_exists():
    assert os.path.exists(CONTENT_PATH), "lp/content.json が存在しません"


def test_required_top_level_keys():
    content = load_content()
    for key in REQUIRED_KEYS:
        assert key in content, f"content.json に '{key}' がありません"


def test_meta_structure():
    content = load_content()
    assert "line_url" in content["meta"]
    assert "colors" in content["meta"]
    for key in ["bg", "text", "accent"]:
        assert key in content["meta"]["colors"], f"colors に '{key}' がありません"


def test_colors_are_correct():
    content = load_content()
    colors = content["meta"]["colors"]
    assert colors["bg"] == "#F5F0E8"
    assert colors["text"] == "#6B1A2A"
    assert colors["accent"] == "#C9A84C"


def test_worries_count():
    content = load_content()
    assert len(content["worries"]) >= 4


def test_ideals_count():
    content = load_content()
    assert len(content["ideals"]) >= 4


def test_story_structure():
    content = load_content()
    assert len(content["story"]) == 6
    for i, part in enumerate(content["story"]):
        assert "title" in part, f"story[{i}] に 'title' がありません"
        assert "body" in part, f"story[{i}] に 'body' がありません"


def test_qa_structure():
    content = load_content()
    assert len(content["qa"]) >= 1
    for i, item in enumerate(content["qa"]):
        assert "q" in item, f"qa[{i}] に 'q' がありません"
        assert "a" in item, f"qa[{i}] に 'a' がありません"


def test_gift_structure():
    content = load_content()
    gift = content["gift"]
    for key in ["title", "description", "items"]:
        assert key in gift, f"gift に '{key}' がありません"
    assert len(gift["items"]) >= 1


def test_profile_structure():
    content = load_content()
    assert "name" in content["profile"]
    assert "body" in content["profile"]
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
python3 -m pytest tests/test_lp.py -v
```

期待: `FAILED` — `lp/content.json が存在しません`

- [ ] **Step 3: lp/content.json を作成する**

```bash
mkdir -p lp/assets
```

`lp/content.json` を作成:

```json
{
  "meta": {
    "line_url": "https://line.me/R/ti/p/YOUR_LINE_ID",
    "colors": {
      "bg": "#F5F0E8",
      "text": "#6B1A2A",
      "accent": "#C9A84C"
    }
  },
  "headline": {
    "catch": "売場で30分迷っていた私が、ラベルを見ただけで自信を持って選べるようになった",
    "sub": "知識ゼロ・予算1,500円からでも、失敗しないイタリアワインの選び方"
  },
  "worries": [
    "売場でラベルを見ても、どれが美味しいのかまったくわからない",
    "毎回同じワインばかり。冒険したいけど、失敗（外れ）が怖い",
    "夫に「このワイン大丈夫？」と言われると、自信をなくしてしまう",
    "宴や会食で、ワインの知識がなくて恥ずかしい思いをしたことがある",
    "ワイン＝フランスのイメージで、イタリアワインは何から学べばいいかわからない",
    "情報が多すぎて、結局どこから手をつければいいのか迷子になっている"
  ],
  "ideals": [
    "ラベルを見ただけで「これは美味しそう」と、確信を持って選びたい",
    "友人や夫に「ワインに詳しいね」と言われたい",
    "イタリア料理とのペアリングを、さらっと提案できる女性になりたい",
    "平日の夕食が、ちょっとリッチで特別な時間に変わってほしい",
    "旅行でイタリアに行ったとき、現地のワインを自信を持って注文したい",
    "一日の疲れを「ちょっと良いグラスワイン1杯」でリセットする習慣がほしい"
  ],
  "gift": {
    "title": "イタリアワイン選び 最短攻略BOOK",
    "subtitle": "＋ 料理別・シーン別 ペアリング早見表つき",
    "description": "知識ゼロ・予算1,500円からでも、スーパーやECで「当たり」を引けるようになる",
    "items": [
      "スーパー・コンビニ・ECで「失敗しない」選び方",
      "価格帯1,500〜3,500円で「当たり」を引く見極め方",
      "迷ったらコレ、の鉄板品種リスト"
    ]
  },
  "cta_text": "今すぐ無料で受け取る",
  "line_steps": [
    "ボタンをクリック",
    "アンケートに回答する",
    "BOOK（PDF）をゲット！"
  ],
  "profile": {
    "name": "Ciro／Hiro（久保田ひろのり）",
    "body": "はじめまして！ここまで読んでくださって、ありがとうございます。\n私はイタリアで6年間ワインを学び、イタリアソムリエ協会（AIS）認定の資格を取得しました。帰国後は東京のイタリア料理店で経験を積み、今でもイタリア好きが講じて、「イタリア人が好むイタリアのワイン」を学び続けています。\n特別な人だけのものに見えるイタリアワインを、「普段の食卓で、自信を持って選べるもの」に変えたい。かつての私自身が「イタリアワイン、難しそう」と一歩を踏み出せなかったからこそ、あなたと同じ目線で、わかりやすくお届けしていきます。"
  },
  "story": [
    {
      "title": "日常・現実の世界",
      "body": "実は、ワインが怖かったんです。\nワインの仕事をしている、と言うと驚かれるのですが、私も昔は、レストランでワインリストを渡されるたびにドキッとしていました。横文字の名前ばかりで、何が違うのかわからない。「とりあえずグラスの赤で」と言って、ホッとする。ワインといえばフランスのイメージしかなくて、イタリアワインなんて、正直まったくの未知の世界でした。"
    },
    {
      "title": "決意",
      "body": "「本場で、ちゃんと学びたい」と決意した\nそんな私が、イタリア料理とワインの世界に惹かれていって、ある日こう思ったんです。「中途半端な知識じゃなくて、本場でちゃんと学びたい」。気づけば私はイタリアにいました。教科書の暗記ではなく、土地と、人と、食卓からワインを学ぶ──そう決めて、6年間を過ごすことになります。"
    },
    {
      "title": "失敗の連続",
      "body": "でも、最初は「情報の多さ」に押しつぶされそうでした\nところが、現実は甘くありませんでした。実はイタリアは、世界でいちばん土着品種が多い国。公式に認められているものだけで350種類以上。州が変われば、ブドウも、味も、合わせる料理もまるで違う。「これ、一生かかっても理解できないんじゃないか…」そう何度も心が折れかけました。"
    },
    {
      "title": "出会い",
      "body": "トスカーナでの「ある出会い」が、すべてを変えた\nたまたま見つかった初めての仕事先に1982年のイタリア最優秀ソムリエがいたんです。一緒に仕事をしているうちに、ワイナリーに行ったり、テイスティング会を企画してくれたり。「この地方では、この料理を食べるから、このワインが生まれた」──そう教わった瞬間、バラバラだった点が、一本の線になりました。"
    },
    {
      "title": "成功の連続",
      "body": "自信を持って選べるようになった\nそこからは、面白いように世界が開けていきました。エノテカ（ワイン店）に入っても、迷わず一本を選べる。料理を見れば、合わせるワインが自然と浮かぶ。「これにしよう」と、自信を持って言える。AISの資格も取り、帰国後は東京のイタリア料理店で、たくさんのお客様にワインをご案内してきました。"
    },
    {
      "title": "体系化",
      "body": "そして気づいた──「あなたの悩み」を解決したい\nワイン選びに必要なのは、難しい専門用語でも、高いお金を払うことでもありません。「州（産地）→ 土着品種 → 料理との合わせ方」この順番で、ほんの少しコツを知るだけ。知識ゼロでも、予算1,500円からでも、あなたの食卓は「おしゃれな大人時間」に変わります。"
    }
  ],
  "why_free": "私自身、昔はワインが「怖くて」、リストを渡されるたびに自信をなくしていました。そんな私が、イタリアで土地と料理からワインを学び、「自分で選べる」喜びを知ったとき、世界がガラッと変わりました。お店でお客様の「私、ワインわからなくて…」という申し訳なさそうな声を聞くたびに、「その壁、私が壊したい」と思ってきました。だからまずは無料で、あなたにも実感してほしいんです。",
  "why_me": "イタリアで6年間、土地と食卓からワインを学んできたこと。イタリアソムリエ協会（AIS）認定の知識に裏打ちされていること。帰国後も東京のイタリア料理店で、たくさんのお客様にご案内してきた現場の経験があること。今もイタリア現地で飲まれているリアルなワインを学び続けていること。ネットや本の受け売りではなく、現地で、いま、私が見て・飲んで・感じている情報を、あなたの食卓のためにわかりやすく翻訳してお届けします。",
  "qa": [
    {
      "q": "なんで公式LINEなんですか？",
      "a": "お渡しするBOOKは容量が大きく、インスタのDMでは送れないんです。DMでやり取りする方とは区別して、お一人おひとりに寄り添ったサポートをするためにも、安心・安全に管理できる公式LINEを使用しています。"
    },
    {
      "q": "仕事が忙しくて、あまり時間が取れません。",
      "a": "だからこそ、です！私自身、お店で働きながら膨大な情報の中から「本当に使えるコツ」だけを絞り込んできました。忙しいあなたが、最短で「選べる人」になれるようにまとめています。時間がないからこそ、私を頼ってください。"
    },
    {
      "q": "ワインの知識がまったくありません。それでも大丈夫ですか？",
      "a": "まったく問題ありません！むしろ「辛口・甘口くらいしか知らない」という方のために作りました。専門用語は最小限。スーパーで今日から使える形でお伝えします。"
    },
    {
      "q": "家に何か届きますか？",
      "a": "届きません！公式LINEにて、PDFでお送りします。住所などの個人情報はいただかないので、ご自宅に何かが届くことはありません。安心して受け取ってください。"
    },
    {
      "q": "個人情報を悪用されたりしませんか？",
      "a": "悪用は一切ありません、と断言させてください。私が使っている公式LINEはセキュリティが厳しく管理されていて、見えるのはアイコンとLINE名のみ。あなたは「一緒にワインを楽しみたい」と思ってくださった大切な仲間です。ご安心ください。"
    },
    {
      "q": "受け取って終わりですか？",
      "a": "いいえ、受け取ってからがスタートです！BOOKをもとに、まずは一本「自分で選んでみる」ところまで伴走します。「読んで終わり」の雑なサポートはしません。あなたの食卓が変わっていく瞬間まで、一緒に楽しんでいきましょう。"
    }
  ],
  "postscript": "あなたの毎日を、もっと豊かにするワインの選び方。\n売場で30分迷って、結局「なんとなく」で買ってしまう。開けてみて「うーん…」と、また自信をなくす。本当はもっと、食事の時間を特別なものにしたいのに。「このワイン、私が選んだの」と、胸を張って言いたいのに。──そうやって、ずっと諦めてきませんでしたか？\n\nでも、大丈夫です。ワイン選びに、難しい知識も、高いお金もいりません。「州 → 品種 → 料理」の順で、ほんの少しコツを知るだけ。知識ゼロでも、予算1,500円からでも、あなたの平日の夜は「おしゃれな大人時間」に変わります。\n\nさあ、今度こそ一緒に、「自分で選べた」という喜びを、手に入れましょう。"
}
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
python3 -m pytest tests/test_lp.py -v
```

期待: 全テスト PASSED

- [ ] **Step 5: コミットする**

```bash
git add lp/content.json lp/assets/.gitkeep tests/test_lp.py
git commit -m "feat: add LP content.json and schema validation tests"
```

---

### Task 2: tools_lp.py — generate_lp() と write_lp() の実装

**Files:**
- Create: `tools_lp.py`
- Modify: `tests/test_lp.py`（HTMLテストを追記）

**Interfaces:**
- Consumes: `lp/content.json`（Task 1で作成）
- Produces:
  - `generate_lp(content: dict, assets_rel: str = "assets") -> str` — HTML文字列を返す
  - `write_lp(content: dict, path: str = "lp/index.html") -> None` — HTMLをファイルに書き出す

- [ ] **Step 1: 失敗するHTMLテストを tests/test_lp.py に追記する**

`tests/test_lp.py` の末尾に追加:

```python
def test_generate_lp_returns_html():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert html.startswith("<!DOCTYPE html>")


def test_generate_lp_contains_all_sections():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert content["headline"]["catch"] in html
    assert content["headline"]["sub"] in html
    assert content["worries"][0] in html
    assert content["ideals"][0] in html
    assert content["gift"]["title"] in html
    assert content["cta_text"] in html
    assert content["meta"]["line_url"] in html
    assert content["profile"]["name"] in html
    assert content["story"][0]["title"] in html
    assert content["qa"][0]["q"] in html
    assert content["postscript"][:20] in html


def test_generate_lp_uses_correct_colors():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "#F5F0E8" in html
    assert "#6B1A2A" in html
    assert "#C9A84C" in html


def test_generate_lp_has_google_fonts():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "fonts.googleapis.com" in html
    assert "Cormorant+Garamond" in html
    assert "Noto+Sans+JP" in html


def test_generate_lp_is_responsive():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "viewport" in html
    assert "max-width" in html


def test_generate_lp_no_cubocci_studio():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert "CUBOCCI STUDIO" not in html


def test_write_lp_outputs_file(tmp_path):
    from tools_lp import generate_lp, write_lp
    content = load_content()
    out_path = str(tmp_path / "index.html")
    write_lp(content, path=out_path)
    with open(out_path, encoding="utf-8") as f:
        text = f.read()
    assert "<!DOCTYPE html>" in text
    assert content["headline"]["catch"] in text
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
python3 -m pytest tests/test_lp.py::test_generate_lp_returns_html -v
```

期待: `FAILED` — `ModuleNotFoundError: No module named 'tools_lp'`

- [ ] **Step 3: tools_lp.py を実装する**

`tools_lp.py` を作成:

```python
import json
import os

LP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lp")
CONTENT_PATH = os.path.join(LP_DIR, "content.json")
OUTPUT_PATH = os.path.join(LP_DIR, "index.html")


def load_content(path: str = CONTENT_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _css(colors: dict) -> str:
    bg, text, accent = colors["bg"], colors["text"], colors["accent"]
    return f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: {bg};
    color: {text};
    font-family: 'Noto Sans JP', sans-serif;
    font-size: 16px;
    line-height: 1.8;
}}
.container {{
    max-width: 720px;
    margin: 0 auto;
    padding: 0 20px;
}}
h1, h2, h3 {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    color: {accent};
    line-height: 1.4;
}}
h1 {{ font-size: clamp(22px, 5vw, 38px); }}
h2 {{ font-size: clamp(20px, 4vw, 28px); margin-bottom: 16px; }}
h3 {{ font-size: clamp(16px, 3vw, 20px); }}
section {{ padding: 60px 0; }}
section:nth-child(even) {{ background: rgba(107,26,42,0.04); }}
.divider {{
    width: 60px; height: 2px;
    background: {accent};
    margin: 16px 0 32px;
}}
ul.bullets {{ list-style: none; padding: 0; }}
ul.bullets li {{
    padding: 10px 0 10px 28px;
    position: relative;
    border-bottom: 1px solid rgba(107,26,42,0.1);
}}
ul.bullets li::before {{
    content: "◆";
    color: {accent};
    position: absolute;
    left: 0;
    font-size: 12px;
    top: 13px;
}}
.cta-btn {{
    display: block;
    width: 100%;
    max-width: 400px;
    margin: 32px auto 0;
    padding: 20px 32px;
    background: {accent};
    color: {text};
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 20px;
    font-weight: bold;
    text-align: center;
    text-decoration: none;
    border-radius: 4px;
    letter-spacing: 1px;
    transition: opacity 0.2s;
}}
.cta-btn:hover {{ opacity: 0.85; }}
.steps {{
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-top: 24px;
}}
.step {{ display: flex; align-items: center; gap: 16px; }}
.step-num {{
    width: 36px; height: 36px;
    background: {text};
    color: {bg};
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    flex-shrink: 0;
}}
.hero {{
    background: {text};
    color: {bg};
    padding: 80px 0 60px;
    text-align: center;
}}
.hero h1 {{ color: {bg}; }}
.hero .sub {{ color: {accent}; margin-top: 20px; font-size: clamp(14px, 3vw, 18px); }}
.hero .deco {{ width: 40px; height: 2px; background: {accent}; margin: 24px auto; }}
.gift-box {{
    border: 2px solid {accent};
    border-radius: 4px;
    padding: 32px;
    margin-top: 24px;
}}
.gift-title {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(20px, 4vw, 28px);
    color: {accent};
    font-weight: bold;
}}
.gift-subtitle {{ opacity: 0.7; margin-bottom: 16px; }}
.story-part {{ margin-bottom: 48px; }}
.story-part h3 {{
    padding-bottom: 8px;
    border-bottom: 1px solid {accent};
    margin-bottom: 16px;
}}
.accordion-item {{ border-bottom: 1px solid rgba(107,26,42,0.2); }}
.accordion-btn {{
    width: 100%;
    background: none;
    border: none;
    padding: 20px 0;
    text-align: left;
    font-size: 15px;
    color: {text};
    font-family: 'Noto Sans JP', sans-serif;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: bold;
}}
.accordion-icon {{ color: {accent}; font-size: 20px; transition: transform 0.2s; }}
.accordion-body {{ display: none; padding: 0 0 20px; line-height: 1.8; }}
.accordion-item.open .accordion-body {{ display: block; }}
.accordion-item.open .accordion-icon {{ transform: rotate(45deg); }}
.profile-name {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: clamp(20px, 4vw, 26px);
    color: {accent};
    margin-bottom: 16px;
}}
.postscript {{ background: {text}; padding: 60px 0; }}
.postscript h2 {{ color: {accent}; }}
.postscript p {{ color: {bg}; }}
.postscript .divider {{ background: {accent}; }}
footer {{ text-align: center; padding: 32px 0; font-size: 12px; opacity: 0.5; }}
@media (min-width: 768px) {{
    .steps {{ flex-direction: row; flex-wrap: wrap; }}
    .step {{ flex: 1; min-width: 180px; }}
}}
"""


def _nl2br(text: str) -> str:
    return text.replace("\n", "<br>")


def generate_lp(content: dict, assets_rel: str = "assets") -> str:
    c = content
    colors = c["meta"]["colors"]
    line_url = c["meta"]["line_url"]

    worries_html = "\n".join(f"<li>{w}</li>" for w in c["worries"])
    ideals_html = "\n".join(f"<li>{i}</li>" for i in c["ideals"])
    gift_items_html = "\n".join(f"<li>{item}</li>" for item in c["gift"]["items"])
    steps_html = "\n".join(
        f'<div class="step"><div class="step-num">{i+1}</div><div>{s}</div></div>'
        for i, s in enumerate(c["line_steps"])
    )
    story_html = "\n".join(
        f'<div class="story-part"><h3>{p["title"]}</h3><p>{_nl2br(p["body"])}</p></div>'
        for p in c["story"]
    )
    qa_html = "\n".join(
        f'''<div class="accordion-item">
  <button class="accordion-btn">Q. {item["q"]}<span class="accordion-icon">+</span></button>
  <div class="accordion-body"><p>{item["a"]}</p></div>
</div>'''
        for item in c["qa"]
    )
    cta_btn = (
        f'<a href="{line_url}" class="cta-btn" target="_blank" rel="noopener">'
        f'{c["cta_text"]}</a>'
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{c["headline"]["catch"]}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Noto+Sans+JP:wght@400;700&display=swap">
  <style>{_css(colors)}</style>
</head>
<body>

<div class="hero">
  <div class="container">
    <h1>{c["headline"]["catch"]}</h1>
    <div class="deco"></div>
    <p class="sub">{c["headline"]["sub"]}</p>
  </div>
</div>

<section>
  <div class="container">
    <h2>こんなお悩みありませんか？</h2>
    <div class="divider"></div>
    <ul class="bullets">{worries_html}</ul>
  </div>
</section>

<section>
  <div class="container">
    <h2>でも…こうなりたい！</h2>
    <div class="divider"></div>
    <ul class="bullets">{ideals_html}</ul>
  </div>
</section>

<section>
  <div class="container">
    <h2>そんなあなたにプレゼント！</h2>
    <div class="divider"></div>
    <div class="gift-box">
      <div class="gift-title">『{c["gift"]["title"]}』</div>
      <div class="gift-subtitle">{c["gift"].get("subtitle", "")}</div>
      <p>{c["gift"]["description"]}</p>
      <ul class="bullets" style="margin-top:16px">{gift_items_html}</ul>
    </div>
  </div>
</section>

<section>
  <div class="container" style="text-align:center">
    <h2>公式LINE追加の手順</h2>
    <div class="divider" style="margin:16px auto 32px"></div>
    <div class="steps">{steps_html}</div>
    {cta_btn}
  </div>
</section>

<section>
  <div class="container">
    <h2>はじめまして</h2>
    <div class="divider"></div>
    <div class="profile-name">{c["profile"]["name"]}</div>
    <p>{_nl2br(c["profile"]["body"])}</p>
  </div>
</section>

<section>
  <div class="container">
    <h2>私のストーリー</h2>
    <div class="divider"></div>
    {story_html}
  </div>
</section>

<section>
  <div class="container">
    <h2>なんで無料なの？</h2>
    <div class="divider"></div>
    <p>{_nl2br(c["why_free"])}</p>
  </div>
</section>

<section>
  <div class="container">
    <h2>あなただからなんです！</h2>
    <div class="divider"></div>
    <p>{_nl2br(c["why_me"])}</p>
  </div>
</section>

<section>
  <div class="container">
    <h2>よくあるご質問</h2>
    <div class="divider"></div>
    <div class="accordion">{qa_html}</div>
  </div>
</section>

<div class="postscript">
  <div class="container">
    <h2>追伸</h2>
    <div class="divider"></div>
    <p>{_nl2br(c["postscript"])}</p>
  </div>
</div>

<section>
  <div class="container" style="text-align:center">
    <h2>さあ、一緒に始めましょう</h2>
    <div class="divider" style="margin:16px auto 32px"></div>
    {cta_btn}
  </div>
</section>

<footer>
  <div class="container">
    <p>© 2026 Ciro／Hiro. All rights reserved.</p>
  </div>
</footer>

<script>
document.querySelectorAll('.accordion-btn').forEach(function(btn) {{
  btn.addEventListener('click', function() {{
    this.parentElement.classList.toggle('open');
  }});
}});
</script>
</body>
</html>"""


def generate_assets(content: dict, assets_dir: str = None) -> dict:
    """Adobe Express MCPを使ってビジュアルアセットを生成する。
    
    セッション外では空辞書を返してスキップする。
    Returns: {"hero": path, "gift_cover": path} or {}
    """
    if assets_dir is None:
        assets_dir = os.path.join(LP_DIR, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    print("ℹ️  generate_assets() はClaude Codeセッション内でAdobe Express MCPを使って実行してください。")
    print(f"   保存先: {assets_dir}")
    print("   必要なファイル:")
    print("   - hero.png (1200x600): ワインレッド背景にゴールドラインのヘッダービジュアル")
    print("   - gift_cover.png (800x1000): BOOKタイトル入り表紙イメージ")
    return {}


def write_lp(content: dict, path: str = OUTPUT_PATH) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    html = generate_lp(content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ LP生成完了: {path}")


if __name__ == "__main__":
    import sys
    c = load_content()
    if "--skip-assets" not in sys.argv:
        generate_assets(c)
    write_lp(c)
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
python3 -m pytest tests/test_lp.py -v
```

期待: 全テスト PASSED

- [ ] **Step 5: 実際にHTMLを生成して目視確認する**

```bash
python3 tools_lp.py --skip-assets
open lp/index.html
```

ブラウザで確認すること:
- ヒービジュアル（ワインレッド背景）が表示されるか
- 全12セクションが正しい順序で表示されるか
- Q&Aをクリックすると開閉するか
- スマホ幅（375px）に縮小したとき崩れないか

- [ ] **Step 6: コミットする**

```bash
git add tools_lp.py tests/test_lp.py
git commit -m "feat: implement generate_lp(), write_lp(), and generate_assets() stub"
```

---

### Task 3: Adobe Express MCPでビジュアルアセット生成

**Files:**
- Create: `lp/assets/hero.png`
- Create: `lp/assets/gift_cover.png`
- Modify: `tools_lp.py`（hero.pngをヘッダーに埋め込む）
- Modify: `tests/test_lp.py`（アセット埋め込みテストを追記）

**Interfaces:**
- Consumes: Adobe Express MCPツール（Claude Codeセッション内で実行）
- Consumes: `generate_lp(content, assets_rel)` — Task 2で定義済み
- Produces: `lp/assets/hero.png`, `lp/assets/gift_cover.png`

Note: このタスクはClaude Codeセッション内でMCPツールを使って手動実行する。

- [ ] **Step 1: 失敗するテストを tests/test_lp.py に追記する**

`tests/test_lp.py` の末尾に追加:

```python
def test_generate_lp_embeds_hero_when_exists(tmp_path):
    from tools_lp import generate_lp
    import shutil
    content = load_content()
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    # ダミーのhero.pngを作成
    (assets_dir / "hero.png").write_bytes(b"\x89PNG\r\n")
    html = generate_lp(content, assets_rel=str(assets_dir))
    assert "hero.png" in html
```

- [ ] **Step 2: テストを実行して失敗を確認する**

```bash
python3 -m pytest tests/test_lp.py::test_generate_lp_embeds_hero_when_exists -v
```

期待: `FAILED` — `assert "hero.png" in html`

- [ ] **Step 3: generate_lp() にhero.png埋め込みロジックを追加する**

`tools_lp.py` の `generate_lp()` 関数内、`.hero` div の直前で assets_rel から hero.png の存在を確認し、あれば背景画像として使う:

`generate_lp()` 関数の最初のブロック（colors 定義の直後）に追加:

```python
    # hero.pngが存在すればCSS背景として使用
    hero_path = os.path.join(assets_rel, "hero.png") if not os.path.isabs(assets_rel) else os.path.join(assets_rel, "hero.png")
    hero_style = f'style="background-image: url(\'{assets_rel}/hero.png\'); background-size: cover; background-position: center;"' if os.path.exists(hero_path) else ""
```

`.hero` div のタグを以下に変更:

```python
    return f"""<!DOCTYPE html>
...
<div class="hero" {hero_style}>
...
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
python3 -m pytest tests/test_lp.py -v
```

期待: 全テスト PASSED

- [ ] **Step 5: Adobe Express MCPでhero.pngを生成する（Claude Codeセッション内）**

Claude Code セッション内で以下を実行（`create_visual_design_express_skill` と Adobe Express MCPを使用）:

生成指示:
- **hero.png**: 幅1200px × 高さ600px。ワインレッド(`#6B1A2A`)の背景。ゴールド(`#C9A84C`)の横ライン装飾。イタリアワインのボトルとグラスをシルエットで配置。テキストなし。
- **gift_cover.png**: 幅800px × 高さ1000px。クリーム(`#F5F0E8`)の背景。ゴールドの枠線。中央に「イタリアワイン選び 最短攻略BOOK」のタイトルをワインレッドで。

生成後、`lp/assets/hero.png` と `lp/assets/gift_cover.png` に保存する。

- [ ] **Step 6: HTMLを再生成して目視確認する**

```bash
python3 tools_lp.py --skip-assets
open lp/index.html
```

hero.pngがヘッダー背景に表示されていることを確認する。

- [ ] **Step 7: コミットする**

```bash
git add tools_lp.py tests/test_lp.py lp/assets/hero.png lp/assets/gift_cover.png
git commit -m "feat: embed hero.png in LP header and add Adobe Express assets"
```

---

### Task 4: GitHub Pages デプロイ

**Files:**
- Modify: なし（GitHub リポジトリ設定は手動・初回のみ）
- Modify: `lp/index.html`（最終版を push）

**Interfaces:**
- Consumes: `lp/index.html`（Task 2/3で生成済み）
- Produces: `https://[username].github.io/ai-org/lp/` でアクセス可能なURL

- [ ] **Step 1: 最終版のindex.htmlを生成する**

```bash
python3 tools_lp.py --skip-assets
```

期待:
```
ℹ️  generate_assets() はClaude Codeセッション内で...
✅ LP生成完了: /Users/kubotahironori/ai-org/lp/index.html
```

- [ ] **Step 2: index.html を git に追加して push する**

```bash
git add lp/index.html lp/assets/
git commit -m "feat: add final LP index.html for GitHub Pages"
git push origin main
```

- [ ] **Step 3: GitHub Pages を有効化する（初回のみ・手動）**

ブラウザで以下を開く:
```
https://github.com/[あなたのGitHubユーザー名]/ai-org/settings/pages
```

設定:
- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/lp`

「Save」をクリック。数分後に公開される。

- [ ] **Step 4: 公開URLにアクセスして確認する**

```
https://[username].github.io/ai-org/
```

確認項目:
- スマホ（375px幅）で全セクションが正しく表示されるか
- CTA ボタンが表示されるか（LINEリンクはまだ仮URLでOK）
- Q&Aアコーディオンが開閉するか
- フォント（Cormorant Garamond / Noto Sans JP）が読み込まれているか

- [ ] **Step 5: LINE URL を設定したら content.json を更新して再公開する**

LINE公式アカウント開設後:

```bash
# lp/content.json の "line_url" を実際のURLに変更
# 例: "https://line.me/R/ti/p/@your_account_id"

python3 tools_lp.py --skip-assets
git add lp/content.json lp/index.html
git commit -m "update: set real LINE URL in LP"
git push origin main
```

---

## スペックカバレッジ確認

| スペック要件 | 対応タスク |
|---|---|
| content.json でテキスト・設定を一元管理 | Task 1 |
| LINE URL を1箇所で管理（全CTAに反映） | Task 1, 2 |
| generate_lp() でHTML生成 | Task 2 |
| 全12セクション実装 | Task 2 |
| クリーム/ワインレッド/ゴールドのカラー | Task 2 |
| スマホ375px基準レスポンシブ、PC最大720px | Task 2 |
| Cormorant Garamond + Noto Sans JP | Task 2 |
| Q&Aアコーディオン（JavaScript） | Task 2 |
| CUBOCCI STUDIO 非表示 | Task 2（テストで保証） |
| write_lp() でファイル出力 | Task 2 |
| generate_assets() Adobe Express MCP | Task 3 |
| hero.png をヘッダーに埋め込み | Task 3 |
| GitHub Pages で無料公開・URL発行 | Task 4 |
| LINE URL 差し替え手順 | Task 4 |
