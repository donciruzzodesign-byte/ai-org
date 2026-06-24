"""
初回セットアップスクリプト。
~/Desktop/CUBOCCI_STUDIO/templates/ にブランドSVGテンプレートを生成する。
実行後はIllustratorで各SVGを開いて微調整できる。
"""
import os
from tools_express import generate_brand_svgs, TEMPLATES_DIR, DESKTOP_DIR

if __name__ == "__main__":
    print("CUBOCCI STUDIO ブランドテンプレートを生成中...")
    paths = generate_brand_svgs()
    print("\n✅ 生成完了:")
    for name, path in paths.items():
        print(f"   {path}")
    print(f"\n📂 フォルダ: {TEMPLATES_DIR}")
    print("\n次のステップ:")
    print("  1. Illustratorで各SVGを開いてデザインを微調整（任意）")
    print("  2. Claude Code で @express を呼び出してAdobe Expressにテンプレートを登録")
    print("  3. runner.py を起動すると毎週火曜にPNGが自動生成されます")
