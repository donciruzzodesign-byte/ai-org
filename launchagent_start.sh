#!/bin/zsh
# ~/.zshrc から ANTHROPIC_API_KEY を読み込む
source ~/.zshrc 2>/dev/null || true

# runner.py を起動
exec /usr/bin/python3 /Users/kubotahironori/Desktop/ai-org/runner.py
