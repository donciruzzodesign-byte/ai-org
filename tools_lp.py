import json
import os
import re

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
.section-image {{ width: 100%; margin-bottom: 24px; overflow: hidden; }}
.section-image img {{ width: 100%; height: auto; display: block; will-change: transform;
    animation: kenburns 10s ease-in-out infinite alternate; }}
@keyframes kenburns {{
  from {{ transform: translateY(var(--py,0px)) scale(1); }}
  to   {{ transform: translateY(var(--py,0px)) scale(1.06); }}
}}
.fade-in {{ opacity: 0; transform: translateY(20px);
    transition: opacity 0.8s ease, transform 0.8s ease; }}
.fade-in.visible {{ opacity: 1; transform: translateY(0); }}
.pw {{ display: inline-block; }}
"""


# 句読点（＋直後の閉じ括弧）で文節を区切るパターン
_PUNCT_RE = re.compile(r"([、。！？]+[」』）]*)")


def _punct_spans(line: str) -> str:
    """句読点の直後だけで折り返されるよう、文節を span.pw で包む。"""
    parts = _PUNCT_RE.split(line)
    segs = []
    for i in range(0, len(parts), 2):
        punct = parts[i + 1] if i + 1 < len(parts) else ""
        if parts[i] or punct:
            segs.append(parts[i] + punct)
    if len(segs) <= 1:
        return line
    return "".join(f'<span class="pw">{s}</span>' for s in segs)


def _fmt(text: str) -> str:
    return "<br>".join(_punct_spans(line) for line in text.split("\n"))


def _section_images(m: dict) -> str:
    if not m:
        return ""
    cols = min(int(m.get("cols", 1) or 1), 3)
    max_width = m.get("max_width", "100%") or "100%"
    urls = [m.get(k, "").replace('"', '%22') for k in ["image", "image2", "image3"]]
    urls = [u for u in urls if u][:cols]
    if not urls:
        return ""
    if len(urls) == 1:
        inner = f'<img src="{urls[0]}" alt="" loading="lazy" style="width:100%;height:auto;display:block;">'
    else:
        imgs = "".join(
            f'<div><img src="{u}" alt="" loading="lazy" style="width:100%;height:auto;display:block;"></div>'
            for u in urls
        )
        inner = f'<div style="display:grid;grid-template-columns:repeat({len(urls)},1fr);gap:8px;">{imgs}</div>'
    mw_style = f"max-width:{max_width};" if max_width != "100%" else ""
    style = f"{mw_style}margin:0 auto 24px;" if mw_style else "margin-bottom:24px;"
    return f'<div class="section-image" style="{style}">{inner}</div>'


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
            f'    <h1>{_fmt(c["headline"]["catch"])}</h1>\n'
            f'    <div class="deco"></div>\n'
            f'    <p class="sub">{_fmt(c["headline"]["sub"])}</p>\n'
            f'  </div></div>\n'
            f'</div>'
        )
    else:
        hero_div = (
            f'<div class="hero" {hero_style}>\n'
            f'  <div class="container">\n'
            f'    <h1>{_fmt(c["headline"]["catch"])}</h1>\n'
            f'    <div class="deco"></div>\n'
            f'    <p class="sub">{_fmt(c["headline"]["sub"])}</p>\n'
            f'  </div>\n'
            f'</div>'
        )

    worries_html = "\n".join(f"<li>{_fmt(w)}</li>" for w in c["worries"])
    ideals_html = "\n".join(f"<li>{_fmt(i)}</li>" for i in c["ideals"])
    gift_items_html = "\n".join(f"<li>{_fmt(item)}</li>" for item in c["gift"]["items"])
    steps_html = "\n".join(
        f'<div class="step"><div class="step-num">{i+1}</div><div>{_fmt(s)}</div></div>'
        for i, s in enumerate(c["line_steps"])
    )
    story_media = media.get("story", [])
    story_html = "\n".join(
        f'<div class="story-part">'
        f'{_section_images(story_media[i] if i < len(story_media) else {})}'
        f'<h3>{p["title"]}</h3><p>{_fmt(p["body"])}</p>'
        f'</div>'
        for i, p in enumerate(c["story"])
    )
    qa_html = "\n".join(
        f'''<div class="accordion-item">
  <button class="accordion-btn">Q. {item["q"]}<span class="accordion-icon">+</span></button>
  <div class="accordion-body"><p>{_fmt(item["a"])}</p></div>
</div>'''
        for item in c["qa"]
    )
    cta_btn = (
        f'<a href="{line_url}" class="cta-btn" target="_blank" rel="noopener">'
        f'{c["cta_text"]}</a>'
    )

    img_worries    = _section_images(media.get("worries",    {}))
    img_ideals     = _section_images(media.get("ideals",     {}))
    img_gift       = _section_images(media.get("gift",       {}))
    img_cta1       = _section_images(media.get("cta1",       {}))
    img_profile    = _section_images(media.get("profile",    {}))
    img_why_free   = _section_images(media.get("why_free",   {}))
    img_why_me     = _section_images(media.get("why_me",     {}))
    img_qa         = _section_images(media.get("qa",         {}))
    img_postscript = _section_images(media.get("postscript", {}))

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
      <div class="gift-subtitle">{_fmt(c["gift"].get("subtitle", ""))}</div>
      <p>{_fmt(c["gift"]["description"])}</p>
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
    <p>{_fmt(c["profile"]["body"])}</p>
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
    <p>{_fmt(c["why_free"])}</p>
  </div>
</section>

<section>
  <div class="container">
    {img_why_me}
    <h2>あなただからなんです！</h2>
    <div class="divider"></div>
    <p>{_fmt(c["why_me"])}</p>
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
    <p>{_fmt(c["postscript"])}</p>
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

// フェードイン on scroll
var fadeObs = new IntersectionObserver(function(entries) {{
  entries.forEach(function(e) {{
    if (e.isIntersecting) {{ e.target.classList.add('visible'); fadeObs.unobserve(e.target); }}
  }});
}}, {{ threshold: 0.1 }});
document.querySelectorAll('.section-image, .story-part, h2, .gift-box, .steps, .profile-name').forEach(function(el) {{
  el.classList.add('fade-in');
  fadeObs.observe(el);
}});

// パララックス + Ken Burns 合成（CSS カスタムプロパティ経由）
function applyParallax() {{
  document.querySelectorAll('.section-image img').forEach(function(img) {{
    var rect = img.closest('.section-image').getBoundingClientRect();
    var offset = (window.innerHeight / 2 - rect.top - rect.height / 2) * 0.07;
    img.style.setProperty('--py', offset + 'px');
  }});
}}
window.addEventListener('scroll', applyParallax, {{ passive: true }});
applyParallax();
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
