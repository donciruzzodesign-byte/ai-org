import os
import sys
import json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock
import tempfile
from tools_video import generate_narration, generate_scene_image, fetch_broll


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
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}

    img_resp = MagicMock()
    img_resp.content = b"fake-png-data"

    with patch("tools_video.requests.post", return_value=gen_resp), \
         patch("tools_video.requests.get", return_value=img_resp):
        result = generate_scene_image("a bottle of Barolo wine", 1, str(tmp_path))

    assert "scene_01.png" in result
    img_path = tmp_path / "images" / "scene_01.png"
    assert img_path.exists()
    assert img_path.read_bytes() == b"fake-png-data"


def test_generate_scene_image_zero_pads_number(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
    img_resp = MagicMock()
    img_resp.content = b"data"

    with patch("tools_video.requests.post", return_value=gen_resp), \
         patch("tools_video.requests.get", return_value=img_resp):
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
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"data": [{"url": "https://example.com/img.png"}]}
    img_resp = MagicMock()
    img_resp.content = b"data"

    with patch("tools_video.requests.post", return_value=gen_resp) as mock_post, \
         patch("tools_video.requests.get", return_value=img_resp):
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
