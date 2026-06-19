import os
import sys
import json
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock
import tempfile
from tools_video import generate_narration


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
