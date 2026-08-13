"""次回の週次自動動画生成（火曜11:00ワイン／12:00コーヒー）で1回だけHiggsfield AI動画生成を許可する。

使い方: リポジトリ直下で `python3 scripts/enable_higgsfield_once.py`
フラグはワイン・コーヒーで別々に消費されるため、同じ週に両方で使いたい場合は
それぞれの自動実行が始まる前にもう一度実行すること。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tools_video import HIGGSFIELD_ONESHOT_FLAG_PATH


def main() -> None:
    with open(HIGGSFIELD_ONESHOT_FLAG_PATH, "w", encoding="utf-8") as f:
        f.write("")
    print(f"✅ 次回の自動動画生成1回分だけHiggsfieldを許可しました: {HIGGSFIELD_ONESHOT_FLAG_PATH}")
    print("   ワイン・コーヒーは別々に消費されます。両方で使いたい場合はそれぞれの回の前に実行してください。")


if __name__ == "__main__":
    main()
