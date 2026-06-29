#!/bin/bash
# LP更新・デプロイスクリプト
set -e
cd "$(dirname "$0")/.."
python3 tools_lp.py
git add docs/
git diff --staged --quiet && echo "変更なし、スキップ" || git commit -m "update: regenerate LP"
git push origin main
echo "✅ LP更新完了。数分後にhttps://donciruzzodesign-byte.github.io/ai-org/ で確認できます"
