import os
import json
import requests
from typing import Optional


VIDEO_TOOL_DEFINITIONS = []  # 後のタスクで完成させる


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


SCENE_IMAGE_STYLE = (
    "High quality food and travel photography, Italian wine, "
    "warm natural golden light, cinematic, 8k resolution, "
)


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


def generate_scene_image(scene_description: str, scene_number: int, output_dir: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY が未設定のためスキップ"

    images_dir = os.path.join(output_dir, "images")
    _ensure_dir(images_dir)
    image_path = os.path.join(images_dir, f"scene_{scene_number:02d}.png")

    if os.path.exists(image_path):
        return f"スキップ（既存）: {image_path}"

    prompt = SCENE_IMAGE_STYLE + scene_description
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "dall-e-3", "prompt": prompt, "size": "1792x1024", "quality": "hd", "n": 1}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            return f"画像生成エラー (scene {scene_number}): {resp.status_code} {resp.text[:200]}"
        image_url = resp.json()["data"][0]["url"]
        img_resp = requests.get(image_url, timeout=60)
        with open(image_path, "wb") as f:
            f.write(img_resp.content)
        return f"画像保存: {image_path}"
    except Exception as e:
        return f"画像生成エラー (scene {scene_number}): {e}"


def fetch_broll(keyword: str, clip_index: int, output_dir: str) -> str:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return "PEXELS_API_KEY が未設定のためスキップ"

    broll_dir = os.path.join(output_dir, "broll")
    _ensure_dir(broll_dir)
    clip_path = os.path.join(broll_dir, f"broll_{clip_index:02d}.mp4")

    if os.path.exists(clip_path):
        return f"スキップ（既存）: {clip_path}"

    try:
        search_url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key}
        params = {"query": keyword, "per_page": 5, "orientation": "landscape", "size": "large"}
        resp = requests.get(search_url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            return f"Pexels検索エラー: {resp.status_code}"

        videos = resp.json().get("videos", [])
        if not videos:
            return f"B-roll素材が見つかりません: {keyword}"

        hd_files = [
            f for f in videos[0]["video_files"]
            if f.get("quality") in ("hd", "uhd") and f.get("width", 0) >= 1280
        ]
        file_url = (hd_files or videos[0]["video_files"])[0]["link"]

        clip_resp = requests.get(file_url, timeout=120, stream=True)
        with open(clip_path, "wb") as f:
            for chunk in clip_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return f"B-roll保存: {clip_path} (キーワード: {keyword})"
    except Exception as e:
        return f"B-roll取得エラー: {e}"
