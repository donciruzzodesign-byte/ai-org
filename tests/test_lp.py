import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CONTENT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "content.json")

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


def test_generate_lp_returns_html():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert html.startswith("<!DOCTYPE html>")


def test_generate_lp_contains_all_sections():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    # 句読点折り返し用の span を除去してから原文の包含を確認
    plain = html.replace('<span class="pw">', "").replace("</span>", "")
    assert content["headline"]["catch"] in plain
    assert content["headline"]["sub"] in plain
    assert content["worries"][0] in plain
    assert content["ideals"][0] in plain
    assert content["gift"]["title"] in plain
    assert content["cta_text"] in plain
    assert content["meta"]["line_url"] in plain
    assert content["profile"]["name"] in plain
    assert content["story"][0]["title"] in plain
    assert content["qa"][0]["q"] in plain
    assert content["postscript"][:20] in plain


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


def test_generate_lp_embeds_hero_when_exists(tmp_path):
    from tools_lp import generate_lp
    content = load_content()
    # header_video が空のときのみ hero.svg フォールバックが使われる
    content.setdefault("media", {})["header_video"] = ""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "hero.svg").write_text("<svg></svg>", encoding="utf-8")
    html = generate_lp(content, assets_rel=str(assets_dir))
    assert "hero.svg" in html


def test_generate_assets_creates_svg_files(tmp_path):
    from tools_lp import generate_assets
    content = load_content()
    assets_dir = tmp_path / "assets"
    result = generate_assets(content, assets_dir=str(assets_dir))
    hero_path = assets_dir / "hero.svg"
    gift_cover_path = assets_dir / "gift_cover.svg"
    assert hero_path.exists(), "hero.svg が生成されていません"
    assert gift_cover_path.exists(), "gift_cover.svg が生成されていません"
    assert "<svg" in hero_path.read_text(encoding="utf-8")
    assert "<svg" in gift_cover_path.read_text(encoding="utf-8")


def test_content_json_media_structure():
    content = load_content()
    assert "media" in content, "content.json に 'media' ブロックがありません"
    m = content["media"]
    assert "header_video" in m
    for key in ["worries", "ideals", "gift", "cta1", "profile", "why_free", "why_me", "qa", "postscript"]:
        assert key in m, f"media に '{key}' がありません"
        assert "image" in m[key], f"media.{key} に 'image' がありません"
    assert "story" in m
    assert len(m["story"]) == 6
    for i, s in enumerate(m["story"]):
        assert "image" in s, f"media.story[{i}] に 'image' がありません"


def test_generate_lp_with_header_video():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["header_video"] = "https://example.com/vineyard.mp4"
    html = generate_lp(content)
    assert "<video" in html
    assert "https://example.com/vineyard.mp4" in html
    assert 'autoplay' in html
    assert 'muted' in html
    assert 'loop' in html


def test_hero_video_has_overlay_for_readability():
    """動画ヘッダーには文字視認性のための暗色オーバーレイと文字影が入る。"""
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["header_video"] = "https://example.com/vineyard.mp4"
    html = generate_lp(content)
    assert '<div class="hero-video-overlay">' in html
    assert ".hero-video-overlay" in html
    assert "text-shadow" in html


def test_line_steps_appear_in_final_cta_section():
    """LINE追加手順は「公式LINE追加の手順」と最終CTAセクションの2箇所に表示される。"""
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert html.count('<div class="steps">') == 2
    final_cta = html.split("さあ、一緒に始めましょう")[1]
    assert '<div class="steps">' in final_cta


def test_generate_lp_without_header_video():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["header_video"] = ""
    html = generate_lp(content)
    assert "<video" not in html
    assert content["headline"]["catch"] in html


def test_generate_lp_with_section_image():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["worries"] = {"image": "https://example.com/worry.jpg"}
    html = generate_lp(content)
    assert 'class="section-image"' in html
    assert "https://example.com/worry.jpg" in html
    # iOS Safari の遅延読み込み不具合を避けるため即時読み込みにしている
    assert 'loading="lazy"' not in html


def test_generate_lp_without_section_image():
    from tools_lp import generate_lp
    content = load_content()
    content["media"] = content.get("media", {})
    content["media"]["worries"] = {"image": ""}
    html = generate_lp(content)
    # section-image div は出力されない（他セクションも空なら）
    # 少なくとも空 URL の img タグは出力されないことを確認
    assert 'src=""' not in html


def test_fmt_wraps_segments_at_punctuation():
    # 句読点（、。！？）の直後だけで折り返せるよう、文節を span.pw で包む
    from tools_lp import _fmt
    html = _fmt("私は昔、ワインが苦手でした。今は大好きです！本当ですよ")
    assert html == (
        '<span class="pw">私は昔、</span>'
        '<span class="pw">ワインが苦手でした。</span>'
        '<span class="pw">今は大好きです！</span>'
        '<span class="pw">本当ですよ</span>'
    )


def test_fmt_keeps_closing_bracket_with_segment():
    # 「。」のような閉じ括弧は直前の文節側に残す
    from tools_lp import _fmt
    html = _fmt("「はじめまして。」と言った、あの日")
    assert '<span class="pw">「はじめまして。」</span>' in html


def test_fmt_without_punctuation_returns_plain_text():
    from tools_lp import _fmt
    assert _fmt("ワイン") == "ワイン"


def test_fmt_converts_newline_to_br():
    from tools_lp import _fmt
    assert _fmt("一行目\n二行目") == "一行目<br>二行目"


def test_generate_lp_has_punct_wrap_style_and_spans():
    from tools_lp import generate_lp
    content = load_content()
    html = generate_lp(content)
    assert 'class="pw"' in html
    assert ".pw" in html  # display:inline-block のスタイル定義


def test_section_images_shows_photo_in_slot2_when_slot1_empty():
    # エディタで「写真1」を空のまま「写真2」だけに画像を入れ、
    # 「カラム数」を初期値の1のまま保存した場合でも、その写真は表示されるべき。
    from tools_lp import _section_images
    m = {"image": "", "cols": "1", "max_width": "100%",
         "image2": "https://example.com/photo2.jpg", "image3": ""}
    html = _section_images(m)
    assert "https://example.com/photo2.jpg" in html
