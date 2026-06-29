import json
import os

LP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
CONTENT_PATH = os.path.join(LP_DIR, "content.json")
OUTPUT_PATH = os.path.join(LP_DIR, "index.html")

FONT_PAIRS = {
    "elegant": {
        "label": "エレガント",
        "heading": "'Cormorant Garamond', Georgia, serif",
        "body": "'Noto Sans JP', sans-serif",
        "gf": "Cormorant+Garamond:wght@400;600;700&family=Noto+Sans+JP:wght@400;700",
    },
    "natural": {
        "label": "ナチュラル",
        "heading": "'Playfair Display', Georgia, serif",
        "body": "'Noto Sans JP', sans-serif",
        "gf": "Playfair+Display:wght@400;700&family=Noto+Sans+JP:wght@400;700",
    },
    "classic": {
        "label": "クラシック",
        "heading": "'EB Garamond', Georgia, serif",
        "body": "'Noto Serif JP', serif",
        "gf": "EB+Garamond:wght@400;700&family=Noto+Serif+JP:wght@400;700",
    },
    "modern": {
        "label": "モダン",
        "heading": "'Montserrat', sans-serif",
        "body": "'Noto Sans JP', sans-serif",
        "gf": "Montserrat:wght@400;600;700&family=Noto+Sans+JP:wght@400;700",
    },
    "wagashi": {
        "label": "和モダン",
        "heading": "'Zen Old Mincho', serif",
        "body": "'Noto Serif JP', serif",
        "gf": "Zen+Old+Mincho:wght@400;700&family=Noto+Serif+JP:wght@400;700",
    },
}


def load_content(path: str = CONTENT_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _css(colors: dict, font_sizes: dict = None, font_pair: str = "elegant") -> str:
    bg, text, accent = colors["bg"], colors["text"], colors["accent"]
    fs = font_sizes or {}
    sz_body = fs.get("body", "16px")
    sz_h1   = fs.get("h1",   "clamp(22px, 5vw, 38px)")
    sz_h2   = fs.get("h2",   "clamp(20px, 4vw, 28px)")
    sz_h3   = fs.get("h3",   "clamp(16px, 3vw, 20px)")
    fp = FONT_PAIRS.get(font_pair, FONT_PAIRS["elegant"])
    heading_family = fp["heading"]
    body_family = fp["body"]
    return f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    background: {bg};
    color: {text};
    font-family: {body_family};
    font-size: {sz_body};
    line-height: 1.8;
}}
.container {{
    max-width: 720px;
    margin: 0 auto;
    padding: 0 20px;
}}
h1, h2, h3 {{
    font-family: {heading_family};
    color: {accent};
    line-height: 1.4;
}}
h1 {{ font-size: {sz_h1}; }}
h2 {{ font-size: {sz_h2}; margin-bottom: 16px; }}
h3 {{ font-size: {sz_h3}; }}
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
    font-family: {heading_family};
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
    flex-direction: row;
    gap: 8px;
    margin-top: 24px;
}}
.step {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 10px;
}}
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
    font-family: {heading_family};
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
    font-family: {body_family};
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
    font-family: {heading_family};
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
}}
.hero {{ position: relative; overflow: hidden; }}
.hero-video {{
    position: absolute; top: 0; left: 0;
    width: 100%; height: 100%;
    object-fit: cover; z-index: 0;
}}
.hero-content {{
    position: relative; z-index: 1;
    padding: 80px 20px 60px;
    text-align: center;
}}
.section-image {{ width: 100%; margin-bottom: 24px; }}
.section-image img {{ width: 100%; height: auto; display: block; }}
"""


def _nl2br(text: str) -> str:
    return text.replace("\n", "<br>")


def _section_image(url: str) -> str:
    if not url:
        return ""
    safe_url = url.replace('"', '%22')
    return f'<div class="section-image"><img src="{safe_url}" alt="" loading="lazy"></div>'


def generate_lp(content: dict, assets_rel: str = "assets") -> str:
    c = content
    meta = c.get("meta", {})
    colors = meta["colors"]
    line_url = meta["line_url"]
    font_pair = meta.get("font_pair", "elegant")
    fp = FONT_PAIRS.get(font_pair, FONT_PAIRS["elegant"])
    gf_url = f"https://fonts.googleapis.com/css2?family={fp['gf']}&display=swap"
    media = c.get("media", {})
    header_video = media.get("header_video", "")

    # hero.svgまたはhero.pngが存在すればCSS背景として使用（SVGを優先）
    def _hero_path(ext: str) -> str:
        base = os.path.join(LP_DIR, assets_rel) if not os.path.isabs(assets_rel) else assets_rel
        return os.path.join(base, f"hero.{ext}")

    if os.path.exists(_hero_path("svg")):
        _hero_rel = f"{assets_rel}/hero.svg"
        hero_style = f'style="background-image: url(\'{_hero_rel}\'); background-size: cover; background-position: center;"'
    elif os.path.exists(_hero_path("png")):
        _hero_rel = f"{assets_rel}/hero.png"
        hero_style = f'style="background-image: url(\'{_hero_rel}\'); background-size: cover; background-position: center;"'
    else:
        hero_style = ""

    if header_video:
        hero_div = (
            f'<div class="hero" style="padding:0;min-height:400px;">\n'
            f'  <video autoplay muted loop playsinline class="hero-video">\n'
            f'    <source src="{header_video}" type="video/mp4">\n'
            f'  </video>\n'
            f'  <div class="hero-content"><div class="container">\n'
            f'    <h1>{_nl2br(c["headline"]["catch"])}</h1>\n'
            f'    <div class="deco"></div>\n'
            f'    <p class="sub">{c["headline"]["sub"]}</p>\n'
            f'  </div></div>\n'
            f'</div>'
        )
    else:
        hero_div = (
            f'<div class="hero" {hero_style}>\n'
            f'  <div class="container">\n'
            f'    <h1>{_nl2br(c["headline"]["catch"])}</h1>\n'
            f'    <div class="deco"></div>\n'
            f'    <p class="sub">{c["headline"]["sub"]}</p>\n'
            f'  </div>\n'
            f'</div>'
        )

    worries_html = "\n".join(f"<li>{w}</li>" for w in c["worries"])
    ideals_html = "\n".join(f"<li>{i}</li>" for i in c["ideals"])
    gift_items_html = "\n".join(f"<li>{item}</li>" for item in c["gift"]["items"])
    steps_html = "\n".join(
        f'<div class="step"><div class="step-num">{i+1}</div><div>{s}</div></div>'
        for i, s in enumerate(c["line_steps"])
    )
    story_media = media.get("story", [])
    story_html = "\n".join(
        f'<div class="story-part">'
        f'{_section_image(story_media[i].get("image", "") if i < len(story_media) else "")}'
        f'<h3>{p["title"]}</h3><p>{_nl2br(p["body"])}</p>'
        f'</div>'
        for i, p in enumerate(c["story"])
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

    img_worries    = _section_image(media.get("worries",    {}).get("image", ""))
    img_ideals     = _section_image(media.get("ideals",     {}).get("image", ""))
    img_gift       = _section_image(media.get("gift",       {}).get("image", ""))
    img_cta1       = _section_image(media.get("cta1",       {}).get("image", ""))
    img_profile    = _section_image(media.get("profile",    {}).get("image", ""))
    img_why_free   = _section_image(media.get("why_free",   {}).get("image", ""))
    img_why_me     = _section_image(media.get("why_me",     {}).get("image", ""))
    img_qa         = _section_image(media.get("qa",         {}).get("image", ""))
    img_postscript = _section_image(media.get("postscript", {}).get("image", ""))

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{c["headline"]["catch"]}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="{gf_url}">
  <style>{_css(colors, meta.get("font_sizes", {}), font_pair)}</style>
</head>
<body>

{hero_div}

<section>
  <div class="container">
    {img_worries}
    <h2>こんなお悩みありませんか？</h2>
    <div class="divider"></div>
    <ul class="bullets">{worries_html}</ul>
  </div>
</section>

<section>
  <div class="container">
    {img_ideals}
    <h2>でも…こうなりたい！</h2>
    <div class="divider"></div>
    <ul class="bullets">{ideals_html}</ul>
  </div>
</section>

<section>
  <div class="container">
    {img_gift}
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
    {img_cta1}
    <h2>公式LINE追加の手順</h2>
    <div class="divider" style="margin:16px auto 32px"></div>
    <div class="steps">{steps_html}</div>
    {cta_btn}
  </div>
</section>

<section>
  <div class="container">
    {img_profile}
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
    {img_why_free}
    <h2>なんで無料なの？</h2>
    <div class="divider"></div>
    <p>{_nl2br(c["why_free"])}</p>
  </div>
</section>

<section>
  <div class="container">
    {img_why_me}
    <h2>あなただからなんです！</h2>
    <div class="divider"></div>
    <p>{_nl2br(c["why_me"])}</p>
  </div>
</section>

<section>
  <div class="container">
    {img_qa}
    <h2>よくあるご質問</h2>
    <div class="divider"></div>
    <div class="accordion">{qa_html}</div>
  </div>
</section>

<div class="postscript">
  <div class="container">
    {img_postscript}
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


def _build_hero_svg() -> str:
    """Generate hero.svg (1200x600) programmatically."""
    # Diagonal decorative lines as subtle texture
    diag_lines = "\n".join(
        f'  <line x1="{x}" y1="0" x2="{x + 600}" y2="600" stroke="#C9A84C" stroke-width="1" opacity="0.15"/>'
        for x in range(-600, 1200, 80)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600" viewBox="0 0 1200 600">
  <!-- Background -->
  <rect width="1200" height="600" fill="#6B1A2A"/>
  <!-- Diagonal texture -->
{diag_lines}
  <!-- Top horizontal gold line -->
  <line x1="0" y1="40" x2="1200" y2="40" stroke="#C9A84C" stroke-width="2"/>
  <!-- Bottom horizontal gold line -->
  <line x1="0" y1="560" x2="1200" y2="560" stroke="#C9A84C" stroke-width="2"/>
  <!-- Minimalist wine glass silhouette (centered, white/cream, subtle) -->
  <g transform="translate(600, 300)" opacity="0.12">
    <!-- Bowl -->
    <ellipse cx="0" cy="-60" rx="60" ry="80" fill="#F5F0E8"/>
    <!-- Stem -->
    <rect x="-4" y="20" width="8" height="80" fill="#F5F0E8"/>
    <!-- Base -->
    <ellipse cx="0" cy="100" rx="36" ry="8" fill="#F5F0E8"/>
    <!-- Inner bowl cutout to make it hollow-ish -->
    <ellipse cx="0" cy="-60" rx="52" ry="70" fill="#6B1A2A" opacity="0.88"/>
  </g>
  <!-- Gold centered text -->
  <text x="600" y="310" font-family="Georgia, serif" font-size="18" fill="#C9A84C"
        text-anchor="middle" letter-spacing="8" opacity="0.6">VINO ITALIANO</text>
</svg>"""


def _build_gift_cover_svg() -> str:
    """Generate gift_cover.svg (800x1000) programmatically."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000" viewBox="0 0 800 1000">
  <!-- Background -->
  <rect width="800" height="1000" fill="#F5F0E8"/>
  <!-- Outer gold border frame (inset 30px) -->
  <rect x="30" y="30" width="740" height="940" fill="none" stroke="#C9A84C" stroke-width="2"/>
  <!-- Inner gold border frame (inset 38px) -->
  <rect x="38" y="38" width="724" height="924" fill="none" stroke="#C9A84C" stroke-width="1" opacity="0.5"/>
  <!-- Title line 1 -->
  <text x="400" y="370" font-family="'Cormorant Garamond', Georgia, serif" font-size="42"
        fill="#6B1A2A" text-anchor="middle" font-weight="600">イタリアワイン選び</text>
  <!-- Title line 2 -->
  <text x="400" y="430" font-family="'Cormorant Garamond', Georgia, serif" font-size="42"
        fill="#6B1A2A" text-anchor="middle" font-weight="600">最短攻略BOOK</text>
  <!-- Gold decorative line between title and subtitle -->
  <line x1="280" y1="470" x2="520" y2="470" stroke="#C9A84C" stroke-width="1.5"/>
  <!-- Subtitle -->
  <text x="400" y="510" font-family="'Noto Sans JP', sans-serif" font-size="18"
        fill="#6B1A2A" text-anchor="middle" opacity="0.8">知識ゼロ・予算1,500円から始める</text>
  <!-- Bottom gold label -->
  <text x="400" y="920" font-family="Georgia, serif" font-size="13" fill="#C9A84C"
        text-anchor="middle" letter-spacing="5">ITALIAN WINE GUIDE</text>
</svg>"""


def generate_assets(content: dict, assets_dir: str = None) -> dict:
    """SVGアセットをプログラムで生成して保存する。

    Returns: {"hero": path_to_hero_svg, "gift_cover": path_to_gift_cover_svg}
    """
    if assets_dir is None:
        assets_dir = os.path.join(LP_DIR, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    hero_path = os.path.join(assets_dir, "hero.svg")
    gift_cover_path = os.path.join(assets_dir, "gift_cover.svg")

    with open(hero_path, "w", encoding="utf-8") as f:
        f.write(_build_hero_svg())
    print(f"✅ hero.svg 生成完了: {hero_path}")

    with open(gift_cover_path, "w", encoding="utf-8") as f:
        f.write(_build_gift_cover_svg())
    print(f"✅ gift_cover.svg 生成完了: {gift_cover_path}")

    return {"hero": hero_path, "gift_cover": gift_cover_path}


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
