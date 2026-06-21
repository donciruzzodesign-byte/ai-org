import os
import json
import requests
from typing import Optional


VIDEO_TOOL_DEFINITIONS = [
    {
        "name": "generate_ae_script",
        "description": "タイムラインデータからAfter Effects用JSXスクリプト(auto_edit.jsx)を生成します。素材を自動配置するスクリプトです。",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline": {
                    "type": "object",
                    "description": "save_timelineと同じ形式のタイムラインデータ"
                },
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"}
            },
            "required": ["timeline", "output_dir"]
        }
    },
    {
        "name": "generate_scene_image",
        "description": "シーン説明からgpt-image-1で画像(1536x1024)を生成して保存します。",
        "input_schema": {
            "type": "object",
            "properties": {
                "scene_description": {"type": "string", "description": "シーンの説明（英語推奨）"},
                "scene_number": {"type": "integer", "description": "シーン番号（1始まり）"},
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"}
            },
            "required": ["scene_description", "scene_number", "output_dir"]
        }
    },
    {
        "name": "fetch_broll",
        "description": "Pexels APIでキーワードに合うB-roll動画素材(.mp4)を取得して保存します。",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "検索キーワード（英語推奨）"},
                "clip_index": {"type": "integer", "description": "クリップ番号（1始まり）"},
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"}
            },
            "required": ["keyword", "clip_index", "output_dir"]
        }
    },
    {
        "name": "save_timeline",
        "description": "タイムラインデータをtimeline.jsonとedit_guide.mdとして保存します。",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline": {
                    "type": "object",
                    "description": "title, duration_sec, narration, scenes, reels_highlights を含むタイムラインデータ"
                },
                "output_dir": {"type": "string", "description": "保存先ディレクトリ"}
            },
            "required": ["timeline", "output_dir"]
        }
    }
]


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

    import base64
    prompt = SCENE_IMAGE_STYLE + scene_description
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gpt-image-1", "prompt": prompt, "size": "1536x1024", "n": 1}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            return f"画像生成エラー (scene {scene_number}): {resp.status_code} {resp.text[:200]}"
        b64_data = resp.json()["data"][0]["b64_json"]
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(b64_data))
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


def save_timeline(timeline: dict, output_dir: str) -> str:
    try:
        _ensure_dir(output_dir)

        json_path = os.path.join(output_dir, "timeline.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)

        guide_path = os.path.join(output_dir, "edit_guide.md")
        title = timeline.get("title", "動画")
        scenes = timeline.get("scenes", [])
        highlights = timeline.get("reels_highlights", [])
        narration = timeline.get("narration", "audio/narration.mp3")

        lines = [
            f"# 編集ガイド：{title}",
            "",
            "## After Effects への読み込み手順",
            f"1. `{narration}` → オーディオレイヤーに配置（自録音の場合はミュート）",
            "2. `images/` → timeline.json の in_sec/out_sec に従いスライドとして配置",
            "3. `broll/` → 各シーン後半にオーバーレイ（opacity 70%推奨）",
            "",
            "## シーン構成",
        ]
        for s in scenes:
            lines.append(f"- シーン{s['id']} ({s['in_sec']}s〜{s['out_sec']}s): {s.get('caption', '')}")
            if s.get("notes"):
                lines.append(f"  ※ {s['notes']}")

        if highlights:
            lines += ["", "## Instagram Reels ハイライト（縦型クロップ推奨）"]
            for h in highlights:
                lines.append(f"- {h['in_sec']}s〜{h['out_sec']}s: {h.get('reason', '')}")

        with open(guide_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return f"タイムライン保存: {json_path}, {guide_path}"
    except Exception as e:
        return f"タイムライン保存エラー: {e}"


def generate_ae_script(timeline: dict, output_dir: str) -> str:
    try:
        _ensure_dir(output_dir)

        title = timeline.get("title", "動画")
        scenes = timeline.get("scenes", [])
        highlights = timeline.get("reels_highlights", [])
        duration = timeline.get("duration_sec", 600)

        def esc(s: str) -> str:
            return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

        def scene_num(sid) -> str:
            if isinstance(sid, str) and "scene_" in sid:
                return sid.replace("scene_", "")
            if isinstance(sid, int):
                return f"{sid:02d}"
            return str(sid)

        L = []  # lines

        L.append("// auto_edit.jsx — After Effects 自動編集スクリプト")
        L.append(f'// タイトル: {esc(title)}')
        L.append("(function() {")
        L.append('    app.beginUndoGroup("Auto Edit");')
        L.append("    try {")
        L.append("")
        L.append(f'    var outputDir = "{esc(output_dir)}";')
        L.append("")
        L.append("    // === YouTube メインコンポジション (1920x1080, 16:9) ===")
        L.append(f'    var comp = app.project.items.addComp("{esc(title)}", 1920, 1080, 1.0, {duration}, 29.97);')
        L.append("    comp.bgColor = [0, 0, 0];")
        L.append("")

        for scene in scenes:
            sid = scene.get("id", "")
            in_sec = scene.get("in_sec", 0)
            out_sec = scene.get("out_sec", 0)
            caption = scene.get("caption", "")
            image_rel = scene.get("image", "")
            broll_rel = scene.get("broll", "")
            v = f"s{scene_num(sid)}"

            L.append(f'    // --- シーン {scene_num(sid)} ({in_sec}s〜{out_sec}s) ---')

            if image_rel:
                img_path = esc(os.path.join(output_dir, image_rel))
                L += [
                    f'    var imgFile_{v} = new File("{img_path}");',
                    f'    if (imgFile_{v}.exists) {{',
                    f'        var imgItem_{v} = app.project.importFile(new ImportOptions(imgFile_{v}));',
                    f'        var imgLayer_{v} = comp.layers.add(imgItem_{v});',
                    f'        imgLayer_{v}.name = "Scene{scene_num(sid)}_Image";',
                    f'        imgLayer_{v}.inPoint = {in_sec};',
                    f'        imgLayer_{v}.outPoint = {out_sec};',
                    f'        imgLayer_{v}.property("Transform").property("Scale").setValue([125, 125]);',
                    f'        imgLayer_{v}.property("Transform").property("Position").setValue([960, 540]);',
                    f'    }}',
                ]

            if broll_rel:
                broll_path = esc(os.path.join(output_dir, broll_rel))
                L += [
                    f'    var brollFile_{v} = new File("{broll_path}");',
                    f'    if (brollFile_{v}.exists) {{',
                    f'        var brollItem_{v} = app.project.importFile(new ImportOptions(brollFile_{v}));',
                    f'        var brollLayer_{v} = comp.layers.add(brollItem_{v});',
                    f'        brollLayer_{v}.name = "Scene{scene_num(sid)}_Broll";',
                    f'        brollLayer_{v}.inPoint = {in_sec};',
                    f'        brollLayer_{v}.outPoint = {out_sec};',
                    f'        brollLayer_{v}.property("Transform").property("Opacity").setValue(70);',
                    f'        brollLayer_{v}.property("Transform").property("Scale").setValue([178, 178]);',
                    f'    }}',
                ]

            if caption:
                L += [
                    f'    var textLayer_{v} = comp.layers.addText("{esc(caption)}");',
                    f'    textLayer_{v}.name = "Scene{scene_num(sid)}_Caption";',
                    f'    textLayer_{v}.inPoint = {in_sec};',
                    f'    textLayer_{v}.outPoint = {out_sec};',
                    f'    var textProp_{v} = textLayer_{v}.property("Source Text");',
                    f'    var textDoc_{v} = textProp_{v}.value;',
                    f'    textDoc_{v}.fontSize = 52;',
                    f'    textDoc_{v}.fillColor = [1.0, 1.0, 1.0];',
                    f'    textDoc_{v}.justification = ParagraphJustification.CENTER_JUSTIFY;',
                    f'    textProp_{v}.setValue(textDoc_{v});',
                    f'    textLayer_{v}.property("Transform").property("Position").setValue([960, 1020]);',
                ]

            L.append("")

        if highlights:
            total_reels = sum(h.get("out_sec", 0) - h.get("in_sec", 0) for h in highlights)
            L.append("    // === Instagram Reels コンポジション (1080x1920, 9:16) ===")
            L.append(f'    var reelsComp = app.project.items.addComp("{esc(title)}_Reels", 1080, 1920, 1.0, {total_reels}, 29.97);')
            L.append("    reelsComp.bgColor = [0, 0, 0];")
            L.append("")

            offset = 0
            for i, h in enumerate(highlights):
                h_in = h.get("in_sec", 0)
                h_out = h.get("out_sec", 0)
                h_dur = h_out - h_in
                for scene in scenes:
                    if scene.get("in_sec", 0) <= h_in < scene.get("out_sec", 0):
                        broll_rel = scene.get("broll", "")
                        if broll_rel:
                            bp = esc(os.path.join(output_dir, broll_rel))
                            L += [
                                f'    var reelsBroll_{i} = new File("{bp}");',
                                f'    if (reelsBroll_{i}.exists) {{',
                                f'        var reelsBrollItem_{i} = app.project.importFile(new ImportOptions(reelsBroll_{i}));',
                                f'        var reelsBrollLayer_{i} = reelsComp.layers.add(reelsBrollItem_{i});',
                                f'        reelsBrollLayer_{i}.name = "Reels_Highlight_{i + 1}";',
                                f'        reelsBrollLayer_{i}.inPoint = {offset};',
                                f'        reelsBrollLayer_{i}.outPoint = {offset + h_dur};',
                                f'        reelsBrollLayer_{i}.property("Transform").property("Scale").setValue([178, 178]);',
                                f'    }}',
                            ]
                        break
                offset += h_dur
            L.append("")

        reels_note = "とReels用（1080x1920）" if highlights else ""
        L += [
            f'    alert("✅ Auto Edit 完了！\\n\\nYouTube用（1920x1080）{reels_note}が作成されました。\\n\\n次のステップ:\\n1. Render Queue を開く\\n2. 出力形式を確認してレンダリング開始\\n\\n出力先: {esc(output_dir)}");',
            "",
            "    } catch(e) {",
            '        alert("エラー: " + e.toString() + "\\nLine: " + e.line);',
            "    }",
            "    app.endUndoGroup();",
            "})();",
        ]

        jsx_path = os.path.join(output_dir, "auto_edit.jsx")
        with open(jsx_path, "w", encoding="utf-8") as f:
            f.write("\n".join(L) + "\n")

        return f"AEスクリプト保存: {jsx_path}"
    except Exception as e:
        return f"AEスクリプト生成エラー: {e}"


def execute_video_tool(name: str, inputs: dict) -> str:
    if name == "generate_ae_script":
        return generate_ae_script(inputs["timeline"], inputs["output_dir"])
    elif name == "generate_narration":
        return generate_narration(inputs["script_text"], inputs["output_dir"])
    elif name == "generate_scene_image":
        return generate_scene_image(inputs["scene_description"], inputs["scene_number"], inputs["output_dir"])
    elif name == "fetch_broll":
        return fetch_broll(inputs["keyword"], inputs["clip_index"], inputs["output_dir"])
    elif name == "save_timeline":
        return save_timeline(inputs["timeline"], inputs["output_dir"])
    return f"不明なツール: {name}"
