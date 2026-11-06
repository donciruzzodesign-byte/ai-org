#!/bin/bash
# ダブルクリックすると、DAY1ページの編集画面がブラウザで開きます。終了はこのウィンドウで Ctrl+C。
cd "$(dirname "$0")" && python3 scripts/page_editor.py --dir docs/day1
