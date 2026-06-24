import os
import re
import shutil
from typing import Optional

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
    if theme not in ("wine", "coffee"):
        raise ValueError(f"Invalid theme '{theme}': must be 'wine' or 'coffee'")
    path = os.path.join(base_dir, f"{date_str}-{theme}")
    _ensure_dir(path)
    return path


def _youtube_thumbnail_svg() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect x="0" y="0" width="640" height="720" fill="{BACKGROUND}"/>
  <text x="320" y="380" font-family="Georgia, serif" fill="{ACCENT}" font-size="22"
        text-anchor="middle" opacity="0.4">IMAGE AREA</text>
  <rect x="640" y="0" width="640" height="720" fill="{PRIMARY}"/>
  <line x1="680" y1="80" x2="1240" y2="80" stroke="{ACCENT}" stroke-width="2"/>
  <line x1="680" y1="640" x2="1240" y2="640" stroke="{ACCENT}" stroke-width="2"/>
  <text data-field="title" x="960" y="310" font-family="'Cormorant Garamond', Georgia, serif" fill="{BACKGROUND}"
        font-size="52" text-anchor="middle" font-weight="bold">{{{{title}}}}</text>
  <text data-field="subtitle" x="960" y="400" font-family="Montserrat, Arial, sans-serif" fill="{ACCENT}"
        font-size="30" text-anchor="middle">{{{{subtitle}}}}</text>
  <text x="960" y="610" font-family="'Cormorant Garamond', Georgia, serif" fill="{ACCENT}"
        font-size="18" text-anchor="middle" letter-spacing="5">{BRAND}</text>
</svg>'''


def _reels_cover_svg() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
  <rect width="1080" height="1920" fill="{PRIMARY}"/>
  <line x1="80" y1="220" x2="1000" y2="220" stroke="{ACCENT}" stroke-width="3"/>
  <line x1="80" y1="1700" x2="1000" y2="1700" stroke="{ACCENT}" stroke-width="3"/>
  <text data-field="title" x="540" y="900" font-family="'Cormorant Garamond', Georgia, serif" fill="{BACKGROUND}"
        font-size="80" text-anchor="middle" font-weight="bold">{{{{title}}}}</text>
  <text data-field="subtitle" x="540" y="1020" font-family="Montserrat, Arial, sans-serif" fill="{ACCENT}"
        font-size="44" text-anchor="middle">{{{{subtitle}}}}</text>
  <text x="540" y="1660" font-family="'Cormorant Garamond', Georgia, serif" fill="{ACCENT}"
        font-size="28" text-anchor="middle" letter-spacing="8">{BRAND}</text>
</svg>'''


def _title_card_svg() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="{BACKGROUND}"/>
  <rect x="50" y="50" width="1820" height="980" fill="none" stroke="{ACCENT}" stroke-width="4"/>
  <rect x="70" y="70" width="1780" height="940" fill="none" stroke="{ACCENT}" stroke-width="1"/>
  <text data-field="title" x="960" y="480" font-family="'Cormorant Garamond', Georgia, serif" fill="{PRIMARY}"
        font-size="88" text-anchor="middle" font-weight="bold">{{{{title}}}}</text>
  <text data-field="subtitle" x="960" y="610" font-family="Montserrat, Arial, sans-serif" fill="{TEXT}"
        font-size="44" text-anchor="middle">{{{{subtitle}}}}</text>
  <text x="960" y="920" font-family="'Cormorant Garamond', Georgia, serif" fill="{ACCENT}"
        font-size="26" text-anchor="middle" letter-spacing="10">{BRAND}</text>
</svg>'''


def generate_brand_svgs(templates_dir: str = TEMPLATES_DIR) -> dict[str, str]:
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
    import subprocess

    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        return png_path
    except (OSError, ImportError):
        pass

    # Fallback: use qlmanage (macOS Quick Look, no extra dependencies)
    ql_path = shutil.which("qlmanage")
    if ql_path is not None:
        out_dir = os.path.dirname(os.path.abspath(png_path))
        _ensure_dir(out_dir)
        r = subprocess.run(
            [ql_path, "-t", "-s", "1920", "-o", out_dir, svg_path],
            capture_output=True,
        )
        ql_out = os.path.join(out_dir, os.path.basename(svg_path) + ".png")
        if r.returncode == 0 and os.path.exists(ql_out):
            os.replace(ql_out, png_path)
            return png_path

    # Fallback: use ImageMagick convert if available
    convert_path = shutil.which("convert")
    if convert_path is None:
        raise RuntimeError(
            "cairo not available, qlmanage failed, and ImageMagick 'convert' not found in PATH. "
            "Run: brew install cairo"
        )
    result = subprocess.run(
        [convert_path, svg_path, png_path],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ImageMagick failed to convert {svg_path}: {result.stderr.decode(errors='replace')}"
        )
    return png_path


def parse_creator_metadata(text: str) -> Optional[dict]:
    matches = list(re.finditer(r"---METADATA---\n(.+?)---END---", text, re.DOTALL))
    if not matches:
        return None
    block = matches[-1].group(1)
    result = {}
    for line in block.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    required = {"title", "subtitle", "keyword", "theme"}
    if not required.issubset(result.keys()):
        return None
    return result


def generate_weekly_assets(
    title: str,
    subtitle: str,
    date_str: str,
    theme: str,
    templates_dir: str = TEMPLATES_DIR,
    base_dir: str = WEEKLY_BASE_DIR,
) -> list[str]:
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
