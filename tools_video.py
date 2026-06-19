import os
import json
import requests
from typing import Optional


VIDEO_TOOL_DEFINITIONS = []  # 後のタスクで完成させる


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_narration(script_text: str, output_dir: str) -> str:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return "ELEVENLABS_API_KEY が未設定のためスキップ"

    audio_dir = os.path.join(output_dir, "audio")
    _ensure_dir(audio_dir)
    audio_path = os.path.join(audio_dir, "narration.mp3")

    if os.path.exists(audio_path):
        return f"スキップ（既存）: {audio_path}"

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": script_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            return f"ナレーション生成エラー: {resp.status_code} {resp.text[:200]}"
        with open(audio_path, "wb") as f:
            f.write(resp.content)
        return f"ナレーション保存: {audio_path}"
    except Exception as e:
        return f"ナレーション生成エラー: {e}"
