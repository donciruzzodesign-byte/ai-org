# Instagram Insights自動連携 セットアップマニュアル

Instagramの投稿分析（いいね・保存・リーチなど）を、毎週手動でコピーする代わりに
自動でスプレッドシートに反映する機能のセットアップ手順です。

この手順は最初の1回だけ、オーナーご自身で行っていただく必要があります。

---

## 1. Instagramをプロアカウントにする

1. Instagramアプリ → 設定 → アカウントの種類とツール
2. 「プロアカウントに切り替える」→ 「クリエイター」または「ビジネス」を選択

すでにプロアカウントになっている場合はこの手順は不要です。

## 2. Facebookページと連携する

1. プロアカウント設定の中の「ページ」または「アカウントセンター」から、
   連携するFacebookページを作成（または既存ページを選択）
2. 画面の案内に沿ってInstagramアカウントと連携する

## 3. Meta for Developersでアプリを作成する

1. https://developers.facebook.com/ にアクセスし、開発者登録
2. 「アプリを作成」→ 種類は「ビジネス」を選択
3. 作成したアプリに「Instagram」プロダクトを追加
4. アプリの設定画面から、連携したFacebookページ・Instagramアカウントを選択

## 4. 長期アクセストークンを発行する

1. Meta for Developersのツール「Graph APIエクスプローラー」を開く
2. 作成したアプリを選択し、`instagram_basic` `instagram_manage_insights` の
   権限にチェックを入れてトークンを生成
3. 生成された短期トークンを、長期トークン（約60日有効）に交換する
   （Graph APIエクスプローラーの案内、または以下のURLで交換）:
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=アプリID&client_secret=アプリシークレット&fb_exchange_token=短期トークン
   ```
4. 発行された長期トークンを `.env` の `META_ACCESS_TOKEN` に設定する
5. InstagramビジネスアカウントのID（数字の羅列）を `.env` の `META_IG_USER_ID` に設定する
   （Graph APIエクスプローラーで `me/accounts` → 該当ページ → `instagram_business_account` から確認できる）

⚠️ このトークンは約60日で失効します。失効すると同期処理が
「トークン期限切れです」というメッセージを出して止まるので、そのタイミングで
このステップ4を再度行ってください。

## 5. Google Cloudサービスアカウントを作成する

1. https://console.cloud.google.com/ でプロジェクトを作成（または既存プロジェクトを使用）
2. 「APIとサービス」→ 「ライブラリ」で Google Sheets API を有効化
3. 「認証情報」→ 「認証情報を作成」→ 「サービスアカウント」を作成
4. 作成したサービスアカウントの「キー」タブから「鍵を追加」→ JSON形式でダウンロード
5. ダウンロードしたJSONファイルを分かりやすい場所に保存し、そのパスを
   `.env` の `GOOGLE_SERVICE_ACCOUNT_JSON` に設定する

## 6. スプレッドシートをサービスアカウントに共有する

1. ダウンロードしたJSONファイルの中の `client_email`（〇〇@〇〇.iam.gserviceaccount.com
   のようなメールアドレス）をコピー
2. 対象のスプレッドシートを開き、右上の「共有」からこのメールアドレスを
   **編集者**権限で追加

## 7. スプレッドシートIDを設定する

スプレッドシートのURL `https://docs.google.com/spreadsheets/d/【この部分】/edit...`
の【この部分】を `.env` の `INSTAGRAM_SHEET_ID` に設定する

---

## 動作確認

すべて設定したら、以下を実行して1回分だけ試してみてください。

```bash
python3 scripts/sync_instagram_insights.py
```

「✅ タブ1: N件処理、タブ2: N件処理」と表示されればOKです。
「❌」や「トークン期限切れ」と出た場合は、上記の手順を見直してください。

以降は毎週水曜08:45に `runner.py` から自動実行されます。
