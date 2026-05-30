#!/bin/bash
set -e

# 既存のuvicornプロセスとポート8765を解放
pkill -f "uvicorn screener.main" 2>/dev/null || true
lsof -ti:8765 | xargs kill -9 2>/dev/null || true
sleep 1

echo "FastAPI サーバーを起動中..."
python3 -m uvicorn screener.main:app --port 8765 &
API_PID=$!

cleanup() {
  echo "終了中..."
  kill $API_PID 2>/dev/null || true
}
trap cleanup EXIT

echo "Electron アプリを起動中..."
cd desktop && npm run dev

wait
