import os
import schedule
import time
from datetime import datetime
from typing import Optional
import anthropic
from tools import TOOL_DEFINITIONS, execute_tool, save_to_notion

_RETRY_DELAYS = [15, 30, 60]


def _with_retry(fn, label):
    """APIConnectionError 時に最大3回リトライしてから再送出。クラッシュ防止のため呼び出し元でも except する。"""
    for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
        try:
            return fn()
        except anthropic.APIConnectionError as e:
            print(f"  ⚠️ {label} 接続エラー（{attempt}/{len(_RETRY_DELAYS)}回目）。{delay}秒後にリトライ...")
            time.sleep(delay)
    try:
        return fn()
    except anthropic.APIConnectionError as e:
        print(f"  ❌ {label} 接続エラー。リトライ上限に達しました。")
        raise

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_env()
client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"


def load_agent(name: str) -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents", f"{name}.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


def save_log(content: str, label: str):
    now = datetime.now()
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", now.strftime("%Y-%m"))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, now.strftime("%Y-%m-%d") + ".txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n=== {label} ({now.strftime('%H:%M')}) ===\n")
        f.write(content)
        f.write("\n")


def run_agent(agent_name: str, prompt: str, label: str, department: Optional[str] = None) -> str:
    system = load_agent(agent_name)
    messages = [{"role": "user", "content": prompt}]

    # ツール使用ループ
    while True:
        response = _with_retry(
            lambda: client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ),
            label,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  🔍 {label} ツール実行: {block.name}({list(block.input.values())[0][:40]}...)")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            save_log(final_text, label)
            now = datetime.now()
            print(f"\n✅ {label} 完了")
            notion_result = save_to_notion(f"{label} ({now.strftime('%Y-%m-%d')})", final_text, department=department)
            print(f"   📝 Notion: {notion_result}")
            return final_text


def _read_todays_log() -> str:
    now = datetime.now()
    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "logs", now.strftime("%Y-%m"), now.strftime("%Y-%m-%d") + ".txt"
    )
    try:
        with open(log_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def monday_task():
    try:
        run_agent(
            "sommelier",
            "今週のコンテンツテーマを1つ提案してください。イタリアワインに関連するテーマで、ターゲット（30〜50代女性、ソムリエ志望）に刺さるものを選んでください。品種・産地・季節・ペアリングの観点から提案してください。",
            "月曜：今週テーマ決定",
            department="ワイン部門",
        )
    except Exception as e:
        print(f"  ❌ 月曜：今週テーマ決定 失敗: {e}")


def tuesday_task():
    try:
        context = _read_todays_log()
        prompt = (
            f"以下の今週のテーマで10分動画の台本を作成してください。\n\n{context}\n\n"
            "テーマ情報がない場合は「イタリアワインの基本：品種と産地の覚え方」で作成してください。"
            "オープニング（1分）・本編（7〜8分）・まとめとCTA（1〜2分）の構成で、話し言葉で書いてください。"
        )
        run_agent("creator", prompt, "火曜：動画台本作成", department="ワイン部門")
    except Exception as e:
        print(f"  ❌ 火曜：動画台本作成 失敗: {e}")


def wednesday_task():
    try:
        message = "台本が完成しました。Notion の各部門ページで確認してください。収録は明日（木曜）の予定です。"
        save_log(message, "水曜：レビュー通知")
        print(f"\n📋 レビュー依頼：Notion のワイン部門・コーヒー部門ページを確認してください。")
    except Exception as e:
        print(f"  ❌ 水曜：レビュー通知 失敗: {e}")


def friday_task():
    try:
        context = _read_todays_log()
        prompt = (
            f"以下の今週のテーマでSNSコンテンツを作成してください。\n\n{context}\n\n"
            "①Instagram カルーセル投稿文（3枚分）"
            "②Instagramキャプション（note誘導リンク付き）"
            "③アフィリエイト商品リスト（楽天・Amazon想定、3点）"
            "をそれぞれ作成してください。"
        )
        run_agent("marketer", prompt, "金曜：SNS投稿文＋商品リスト", department="ワイン部門")
    except Exception as e:
        print(f"  ❌ 金曜：SNS投稿文＋商品リスト 失敗: {e}")


def sunday_task():
    try:
        run_agent(
            "marketer",
            "今週のSNS投稿（Instagram・YouTube）の反応を分析するレポートテンプレートを作成してください。"
            "確認すべき指標（リーチ・いいね・保存・フォロワー増加など）と来週への改善提案フォーマットを含めてください。",
            "日曜：反応分析レポート",
        )
    except Exception as e:
        print(f"  ❌ 日曜：反応分析レポート 失敗: {e}")


def regional_wines_task():
    try:
        _regional_wines_task_inner()
    except Exception as e:
        print(f"  ❌ 月曜：州別おすすめワイン紹介 失敗: {e}")


def _regional_wines_task_inner():
    context = _read_todays_log()
    prompt = (
        f"以下の今週のテーマ・産地情報を参考にしながら、今週取り上げるイタリアの州を1つ選び、"
        "その州のおすすめワインを以下の形式で紹介してください。\n\n"
        f"{context}\n\n"
        "【出力形式】\n"
        "## 今週の州：〇〇州（イタリア語名）\n\n"
        "### 泡（スパークリング）\n"
        "- ワイン名：\n- 品種：\n- 特徴：\n- おすすめペアリング：\n\n"
        "### 白ワイン\n"
        "- ワイン名：\n- 品種：\n- 特徴：\n- おすすめペアリング：\n\n"
        "### 赤ワイン\n"
        "- ワイン名：\n- 品種：\n- 特徴：\n- おすすめペアリング：\n\n"
        "【ルール】\n"
        "- 泡のないシチリアなど一部の州は、泡の代わりに白か赤のどちらかを1本追加して合計3本にしてください\n"
        "- 各ワインはソムリエ試験の頻出銘柄・品種を優先してください\n"
        "- 30〜50代女性・ソムリエ志望者にわかりやすい言葉で書いてください\n"
        "- Instagram投稿やnote記事にそのまま使えるレベルで仕上げてください"
    )
    run_agent("sommelier", prompt, "月曜：州別おすすめワイン紹介", department="ワイン部門")


def collab_task(theme: str):
    """ソムリエが深堀り → クリエイターが台本＋スライドに変換する連携タスク。app.py から手動で呼び出す。"""
    try:
        sommelier_output = run_agent(
            "sommelier",
            f"以下のテーマについて、動画コンテンツに使える詳細な専門知識をまとめてください。\n\nテーマ：{theme}\n\n"
            "品種・産地・製法・ペアリング・ソムリエ試験ポイントを網羅し、クリエイターが台本を書きやすいよう構造化してください。",
            f"連携：ソムリエ調査（{theme}）",
            department="ワイン部門",
        )
        run_agent(
            "creator",
            f"以下のソムリエによる専門知識をもとに、10分動画の台本とスライド構成を作成してください。\n\n{sommelier_output}",
            f"連携：クリエイター台本＋スライド（{theme}）",
            department="ワイン部門",
        )
    except Exception as e:
        print(f"  ❌ 連携タスク失敗: {e}")


def coffee_monday_task():
    try:
        run_agent(
            "barista",
            "今週のコーヒーコンテンツテーマを1つ提案してください。イタリアコーヒーに関連するテーマで、"
            "ターゲット（30〜50代女性、コーヒー文化・ワインに興味がある方）に刺さるものを選んでください。"
            "産地・抽出方法・バール文化・季節・ペアリングの観点から提案してください。",
            "月曜：コーヒーテーマ決定",
            department="コーヒー部門",
        )
    except Exception as e:
        print(f"  ❌ 月曜：コーヒーテーマ決定 失敗: {e}")


def coffee_regional_task():
    try:
        context = _read_todays_log()
        prompt = (
            f"以下の今週のコーヒーテーマを参考にしながら、今週取り上げるイタリアの地域・都市を1つ選び、"
            "その地域のコーヒー文化を以下の形式で紹介してください。\n\n"
            f"{context}\n\n"
            "【出力形式】\n"
            "## 今週の地域：〇〇（イタリア語名）\n\n"
            "### エスプレッソ\n"
            "- ブレンド/豆名：\n- 産地/ロースター：\n- 特徴：\n- おすすめペアリング：\n\n"
            "### フィルターコーヒー（またはモカ）\n"
            "- 豆名：\n- 産地：\n- 特徴：\n- おすすめペアリング：\n\n"
            "### 食とのペアリング\n"
            "- 定番の組み合わせ：\n- ペアリングのポイント：\n\n"
            "【ルール】\n"
            "- 各地域のバール文化・エピソードを必ず1つ添えてください\n"
            "- IIAC鑑定基準（アロマ・苦味・酸味・ボディ）に触れてください\n"
            "- 30〜50代女性・コーヒー初中級者にわかりやすい言葉で書いてください\n"
            "- Instagram投稿やnote記事にそのまま使えるレベルで仕上げてください"
        )
        run_agent("barista", prompt, "月曜：地域別コーヒー紹介", department="コーヒー部門")
    except Exception as e:
        print(f"  ❌ 月曜：地域別コーヒー紹介 失敗: {e}")


def coffee_tuesday_task():
    try:
        context = _read_todays_log()
        prompt = (
            f"以下の今週のコーヒーテーマで10分動画の台本を作成してください。\n\n{context}\n\n"
            "テーマ情報がない場合は「イタリアコーヒーの基本：エスプレッソ文化とバールの楽しみ方」で作成してください。"
            "オープニング（1分）・本編（7〜8分）・まとめとCTA（1〜2分）の構成で、話し言葉で書いてください。"
        )
        run_agent("creator", prompt, "火曜：コーヒー動画台本作成", department="コーヒー部門")
    except Exception as e:
        print(f"  ❌ 火曜：コーヒー動画台本作成 失敗: {e}")


def coffee_friday_task():
    try:
        context = _read_todays_log()
        prompt = (
            f"以下の今週のコーヒーテーマでSNSコンテンツを作成してください。\n\n{context}\n\n"
            "①Instagram カルーセル投稿文（3枚分）"
            "②Instagramキャプション（note誘導リンク付き）"
            "③アフィリエイト商品リスト（楽天・Amazon想定、コーヒー豆・器具3点）"
            "をそれぞれ作成してください。"
        )
        run_agent("marketer", prompt, "金曜：コーヒーSNS投稿文＋商品リスト", department="コーヒー部門")
    except Exception as e:
        print(f"  ❌ 金曜：コーヒーSNS投稿文＋商品リスト 失敗: {e}")


def main():
    schedule.every().monday.at("09:00").do(monday_task)
    schedule.every().monday.at("09:30").do(regional_wines_task)
    schedule.every().tuesday.at("09:00").do(tuesday_task)
    schedule.every().wednesday.at("09:00").do(wednesday_task)
    schedule.every().friday.at("09:00").do(friday_task)
    schedule.every().sunday.at("20:00").do(sunday_task)
    schedule.every().monday.at("10:00").do(coffee_monday_task)
    schedule.every().monday.at("10:30").do(coffee_regional_task)
    schedule.every().tuesday.at("10:00").do(coffee_tuesday_task)
    schedule.every().friday.at("10:00").do(coffee_friday_task)

    print("=" * 50)
    print("AI組織 週次スケジューラー起動中")
    print("月09:00 テーマ決定 / 月09:30 州別ワイン紹介 / 火09:00 台本")
    print("水09:00 レビュー通知 / 金09:00 SNS投稿文 / 日20:00 反応分析")
    print("月10:00 コーヒーテーマ / 月10:30 地域別コーヒー / 火10:00 コーヒー台本 / 金10:00 コーヒーSNS")
    print("停止するには Ctrl+C")
    print("=" * 50)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
