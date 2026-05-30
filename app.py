import os
import anthropic
from tools import TOOL_DEFINITIONS, execute_tool, save_to_notion
from runner import collab_task

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

AGENTS = {
    "1": ("ceo",       "CEO",        "全体指揮・タスク調整"),
    "2": ("sommelier", "ソムリエ",   "ワイン専門知識・テーマ提案・論文検索"),
    "3": ("creator",   "クリエイター", "動画台本・構成・スライド作成"),
    "4": ("marketer",  "マーケター",  "SNS投稿文・集客・トレンド調査"),
    "5": ("collab",    "連携企画",    "ソムリエ→クリエイター連携（台本＋スライド）"),
    "6": ("barista",   "バリスタ",   "イタリアコーヒー専門知識・テーマ提案"),
}

TOOL_LABEL = {
    "web_search":    "🔍 Web検索",
    "search_papers": "📄 論文検索",
    "fetch_page":    "📖 ページ取得",
}


def load_agent(name: str) -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents", f"{name}.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


def select_agent() -> tuple:
    print("=" * 50)
    print("CUBOCCI STUDIO AI組織チャット")
    print("Web検索・論文検索・ページ取得対応")
    print("=" * 50)
    print("\nどのエージェントに話しかけますか？\n")
    for key, (_, label, desc) in AGENTS.items():
        print(f"  {key}. {label}（{desc}）")
    print()

    while True:
        choice = input("番号を入力（1〜6）: ").strip()
        if choice in AGENTS:
            agent_id, label, _ = AGENTS[choice]
            return agent_id, label
        print("1〜6の番号を入力してください。")


def chat(agent_id: str, label: str) -> bool:
    system_prompt = load_agent(agent_id)
    history = []

    print(f"\n{'=' * 50}")
    print(f"{label}と会話中")
    print("終了: quit／エージェント切替: /switch")
    print("=" * 50)

    while True:
        user_input = input("\nあなた: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "終了"):
            print("チャットを終了します。")
            return False
        if user_input.lower() == "/switch":
            return True

        history.append({"role": "user", "content": user_input})

        # ツール使用ループ
        while True:
            response = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=history,
            )

            if response.stop_reason == "tool_use":
                history.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        query_preview = str(list(block.input.values())[0])[:50]
                        print(f"\n{TOOL_LABEL.get(block.name, block.name)}: {query_preview}...")
                        result = execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                history.append({"role": "user", "content": tool_results})

            else:
                final_text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                history.append({"role": "assistant", "content": final_text})
                print(f"\n{label}: {final_text}")
                from datetime import datetime
                title = f"{label} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                notion_result = save_to_notion(title, final_text)
                print(f"\n📝 Notion: {notion_result}")
                break


if __name__ == "__main__":
    while True:
        agent_id, label = select_agent()
        if agent_id == "collab":
            theme = input("\n連携テーマを入力してください: ").strip()
            if theme:
                collab_task(theme)
            continue
        should_switch = chat(agent_id, label)
        if not should_switch:
            break
