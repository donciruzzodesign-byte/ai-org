# CUBOCCI STUDIO AI組織

週次ワインコンテンツを自動生成するAIエージェントシステム。

## セットアップ

```bash
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-xxxxxx"  # 実際のキーを設定
```

## 使い方

### 手動でCEOに指示する

```bash
python3 app.py
```

### 週次スケジューラーを起動する（以降毎週自動実行）

```bash
python3 runner.py
```

Mac起動時に自動実行したい場合はLaunchAgentに登録してください。

## 週次スケジュール

| 曜日 | 時刻 | 内容 |
|------|------|------|
| 月 | 09:00 | 今週テーマ決定（ソムリエ） |
| 火 | 09:00 | 動画台本作成（クリエイター） |
| 水 | 09:00 | レビュー通知（手動確認） |
| 木 | - | 動画収録・編集（オーナー手動） |
| 金 | 09:00 | SNS投稿文＋商品リスト（マーケター） |
| 土 | - | 動画公開＋SNS投稿（オーナー手動） |
| 日 | 20:00 | 反応分析レポート（マーケター） |

## ログ確認

```bash
cat logs/YYYY-MM-DD.txt
```
# ai-org
