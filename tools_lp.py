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
