import os
import sys
import json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock
import tempfile
from tools_video import generate_narration, generate_scene_image, fetch_broll, generate_ae_script


def test_generate_narration_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    result = generate_narration("テスト台本", str(tmp_path))
    assert "未設定" in result


def test_generate_narration_saves_mp3(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice-123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake-audio-data"

    with patch("tools_video.requests.post", return_value=mock_resp):
        result = generate_narration("テスト台本", str(tmp_path))

    assert "narration.mp3" in result
    audio_path = tmp_path / "audio" / "narration.mp3"
    assert audio_path.exists()
    assert audio_path.read_bytes() == b"fake-audio-data"


def test_generate_narration_skips_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "narration.mp3").write_bytes(b"existing")

    with patch("tools_video.requests.post") as mock_post:
        result = generate_narration("台本", str(tmp_path))

    mock_post.assert_not_called()
    assert "スキップ" in result


def test_generate_narration_returns_error_on_api_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("tools_video.requests.post", return_value=mock_resp):
        result = generate_narration("台本", str(tmp_path))

    assert "エラー" in result


def test_generate_scene_image_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = generate_scene_image("a bottle of Barolo wine", 1, str(tmp_path))
    assert "未設定" in result


def test_generate_scene_image_saves_png(monkeypatch, tmp_path):
    import base64
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"b64_json": base64.b64encode(b"fake-png-data").decode()}]}

    with patch("tools_video.requests.post", return_value=gen_resp):
        result = generate_scene_image("a bottle of Barolo wine", 1, str(tmp_path))

    assert "scene_01.png" in result
    img_path = tmp_path / "images" / "scene_01.png"
    assert img_path.exists()
    assert img_path.read_bytes() == b"fake-png-data"


def test_generate_scene_image_zero_pads_number(monkeypatch, tmp_path):
    import base64
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"b64_json": base64.b64encode(b"data").decode()}]}

    with patch("tools_video.requests.post", return_value=gen_resp):
        generate_scene_image("vineyard at sunset", 9, str(tmp_path))

    assert (tmp_path / "images" / "scene_09.png").exists()


def test_generate_scene_image_skips_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "scene_01.png").write_bytes(b"existing")

    with patch("tools_video.requests.post") as mock_post:
        result = generate_scene_image("wine", 1, str(tmp_path))

    mock_post.assert_not_called()
    assert "スキップ" in result


def test_generate_scene_image_prepends_style_prefix(monkeypatch, tmp_path):
    import base64
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"b64_json": base64.b64encode(b"data").decode()}]}

    with patch("tools_video.requests.post", return_value=gen_resp) as mock_post:
        generate_scene_image("Barolo bottle", 1, str(tmp_path))

    sent_prompt = mock_post.call_args[1]["json"]["prompt"]
    assert "High quality" in sent_prompt
    assert "Barolo bottle" in sent_prompt


def test_fetch_broll_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    result = fetch_broll("Italian vineyard", 1, str(tmp_path))
    assert "未設定" in result


def test_fetch_broll_saves_mp4(monkeypatch, tmp_path):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")

    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.json.return_value = {
        "videos": [{
            "video_files": [
                {"link": "https://example.com/hd.mp4", "quality": "hd", "width": 1280, "height": 720}
            ]
        }]
    }

    clip_resp = MagicMock()
    clip_resp.iter_content = MagicMock(return_value=[b"fake-video-data"])

    with patch("tools_video.requests.get", side_effect=[search_resp, clip_resp]):
        result = fetch_broll("Italian vineyard", 1, str(tmp_path))

    assert "broll_01.mp4" in result
    clip_path = tmp_path / "broll" / "broll_01.mp4"
    assert clip_path.exists()


def test_fetch_broll_skips_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    broll_dir = tmp_path / "broll"
    broll_dir.mkdir()
    (broll_dir / "broll_01.mp4").write_bytes(b"existing")

    with patch("tools_video.requests.get") as mock_get:
        result = fetch_broll("wine", 1, str(tmp_path))

    mock_get.assert_not_called()
    assert "スキップ" in result


def test_fetch_broll_returns_message_when_no_videos(monkeypatch, tmp_path):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")

    search_resp = MagicMock()
    search_resp.status_code = 200
    search_resp.json.return_value = {"videos": []}

    with patch("tools_video.requests.get", return_value=search_resp):
        result = fetch_broll("xyznotfound", 1, str(tmp_path))

    assert "見つかりません" in result


from tools_video import save_timeline, execute_video_tool


SAMPLE_TIMELINE = {
    "title": "バローロ特集",
    "duration_sec": 600,
    "narration": "audio/narration.mp3",
    "scenes": [
        {
            "id": 1, "in_sec": 0, "out_sec": 60,
            "type": "slide", "image": "images/scene_01.png",
            "broll": "broll/broll_01.mp4",
            "caption": "バローロはなぜ「ワインの王」と呼ばれるのか？",
            "notes": "テロップは画面下部"
        }
    ],
    "reels_highlights": [
        {"id": 1, "in_sec": 45, "out_sec": 75, "reason": "最も印象的なフレーズ"}
    ]
}


def test_save_timeline_creates_json(tmp_path):
    result = save_timeline(SAMPLE_TIMELINE, str(tmp_path))
    assert "timeline.json" in result
    json_path = tmp_path / "timeline.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["title"] == "バローロ特集"
    assert len(data["scenes"]) == 1


def test_save_timeline_creates_edit_guide_md(tmp_path):
    save_timeline(SAMPLE_TIMELINE, str(tmp_path))
    guide_path = tmp_path / "edit_guide.md"
    assert guide_path.exists()
    content = guide_path.read_text(encoding="utf-8")
    assert "バローロ特集" in content
    assert "After Effects" in content
    assert "Reels" in content
    assert "0s〜60s" in content


def test_execute_video_tool_dispatches_generate_narration(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    result = execute_video_tool("generate_narration", {
        "script_text": "テスト", "output_dir": str(tmp_path)
    })
    assert "未設定" in result


def test_execute_video_tool_dispatches_generate_scene_image(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = execute_video_tool("generate_scene_image", {
        "scene_description": "wine", "scene_number": 1, "output_dir": str(tmp_path)
    })
    assert "未設定" in result


def test_execute_video_tool_dispatches_fetch_broll(monkeypatch, tmp_path):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    result = execute_video_tool("fetch_broll", {
        "keyword": "wine", "clip_index": 1, "output_dir": str(tmp_path)
    })
    assert "未設定" in result


def test_execute_video_tool_dispatches_save_timeline(tmp_path):
    result = execute_video_tool("save_timeline", {
        "timeline": SAMPLE_TIMELINE, "output_dir": str(tmp_path)
    })
    assert "timeline.json" in result


def test_execute_video_tool_returns_error_for_unknown(tmp_path):
    result = execute_video_tool("unknown_tool", {})
    assert "不明" in result


def test_generate_ae_script_creates_jsx(tmp_path):
    result = generate_ae_script(SAMPLE_TIMELINE, str(tmp_path))
    assert "auto_edit.jsx" in result
    jsx_path = tmp_path / "auto_edit.jsx"
    assert jsx_path.exists()


def test_generate_ae_script_jsx_contains_title(tmp_path):
    generate_ae_script(SAMPLE_TIMELINE, str(tmp_path))
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "バローロ特集" in content


def test_generate_ae_script_jsx_references_image(tmp_path):
    generate_ae_script(SAMPLE_TIMELINE, str(tmp_path))
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "scene_01.png" in content


def test_generate_ae_script_jsx_references_broll(tmp_path):
    generate_ae_script(SAMPLE_TIMELINE, str(tmp_path))
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "broll_01.mp4" in content


def test_generate_ae_script_jsx_sets_in_out_points(tmp_path):
    generate_ae_script(SAMPLE_TIMELINE, str(tmp_path))
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "inPoint = 0" in content
    assert "outPoint = 60" in content


def test_generate_ae_script_jsx_creates_reels_comp(tmp_path):
    generate_ae_script(SAMPLE_TIMELINE, str(tmp_path))
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "Reels" in content
    assert "1080, 1920" in content


def test_generate_ae_script_works_without_highlights(tmp_path):
    timeline_no_highlights = {**SAMPLE_TIMELINE, "reels_highlights": []}
    result = generate_ae_script(timeline_no_highlights, str(tmp_path))
    assert "auto_edit.jsx" in result
    content = (tmp_path / "auto_edit.jsx").read_text(encoding="utf-8")
    assert "1920, 1080" in content


def test_execute_video_tool_dispatches_generate_ae_script(tmp_path):
    result = execute_video_tool("generate_ae_script", {
        "timeline": SAMPLE_TIMELINE, "output_dir": str(tmp_path)
    })
    assert "auto_edit.jsx" in result


from tools_video import analyze_image, scan_photos


def test_scan_photos_returns_empty_when_no_folder(tmp_path):
    result = scan_photos(str(tmp_path))
    assert result == "[]"


def test_scan_photos_analyzes_each_photo(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    (photos / "barolo.jpg").write_bytes(b"a")
    (photos / "vineyard.png").write_bytes(b"b")

    with patch("tools_video.analyze_image", return_value="解析結果") as mock_analyze:
        result = scan_photos(str(tmp_path))

    data = json.loads(result)
    assert len(data) == 2
    files = {d["file"] for d in data}
    assert files == {"barolo.jpg", "vineyard.png"}
    assert all(d["analysis"] == "解析結果" for d in data)
    assert mock_analyze.call_count == 2


def test_scan_photos_ignores_non_images(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    (photos / "note.txt").write_text("x")
    (photos / "wine.jpg").write_bytes(b"a")

    with patch("tools_video.analyze_image", return_value="ok"):
        result = scan_photos(str(tmp_path))

    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["file"] == "wine.jpg"


def test_analyze_image_skips_when_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    img = tmp_path / "x.png"
    img.write_bytes(b"fake")
    result = analyze_image(str(img), "何が写っていますか")
    assert "未設定" in result


def test_analyze_image_returns_error_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    result = analyze_image(str(tmp_path / "nope.png"), "説明して")
    assert "見つかりません" in result


def test_analyze_image_returns_vision_text(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    img = tmp_path / "barolo.png"
    img.write_bytes(b"fake-png")

    text_block = MagicMock()
    text_block.text = "バローロの瓶が写っています"
    resp = MagicMock()
    resp.content = [text_block]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = resp

    with patch("tools_video.anthropic.Anthropic", return_value=mock_client):
        result = analyze_image(str(img), "何が写っていますか")

    assert result == "バローロの瓶が写っています"
    sent = mock_client.messages.create.call_args[1]
    content = sent["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    assert content[1]["text"] == "何が写っていますか"


from tools_video import assign_photo
from PIL import Image


def _make_photo(path, size=(4000, 2000)):
    Image.new("RGB", size, (120, 40, 40)).save(path)


def test_assign_photo_missing_source(tmp_path):
    result = assign_photo("nope.jpg", 1, str(tmp_path))
    assert "見つかりません" in result


def test_assign_photo_creates_normalized_png(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    _make_photo(photos / "barolo.jpg", size=(4000, 2000))

    result = assign_photo("barolo.jpg", 3, str(tmp_path))

    assert "scene_03.png" in result
    out = tmp_path / "images" / "scene_03.png"
    assert out.exists()
    with Image.open(out) as im:
        assert im.size == (1536, 1024)


def test_assign_photo_handles_portrait_source(tmp_path):
    photos = tmp_path / "my_photos"
    photos.mkdir()
    _make_photo(photos / "tall.jpg", size=(1000, 3000))

    assign_photo("tall.jpg", 1, str(tmp_path))

    with Image.open(tmp_path / "images" / "scene_01.png") as im:
        assert im.size == (1536, 1024)
