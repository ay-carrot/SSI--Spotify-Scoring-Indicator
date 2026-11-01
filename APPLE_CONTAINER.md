# Apple `container` CLI での動作確認

Docker Desktopの代わりに、Apple純正の `container` CLI(macOS 26 "Tahoe" 以降 / Apple Silicon専用)でこのアプリを動かす手順です。
`docker-compose`相当のネイティブ機能はまだ無いため、`scripts/run-apple-container.sh`で3つのコンテナ
(PostgreSQL / バックエンド / フロントエンド)を個別に起動します。
Docker Desktop・OrbStack・Colimaなどを使う場合は、`docker-compose.yml`の方が簡単です(ルートの`README.md`参照)。

## 前提条件

- Apple Silicon Mac(M1以降)
- macOS 26(Tahoe)推奨。macOS 15でも動きますが、コンテナ間ネットワークに制限があります
- `container` CLI がインストール済み
  ```bash
  brew install --cask container
  # または https://github.com/apple/container の最新 .pkg をダウンロード
  ```

## セットアップ

1. Spotify Developer Dashboardの登録と`backend/.env`の準備

   ルートの`README.md`のセットアップ手順1・2に従ってください。
   `DATABASE_URL`はスクリプトが自動で上書きするので、コンテナの動作には影響しません。

2. 起動スクリプトを実行

   ```bash
   chmod +x scripts/run-apple-container.sh
   ./scripts/run-apple-container.sh up
   ```

   内部で行っていること:
   1. `container system start` でサービス起動
   2. `container network create` でアプリ専用ネットワークを作成
   3. PostgreSQLコンテナを起動しヘルスチェック
   4. `container inspect` でPostgreSQLコンテナのIPアドレスを取得
   5. `backend/Dockerfile` をビルドして起動(`DATABASE_URL` に取得したIPを直接埋め込む)
   6. バックエンドのIPアドレスも同様に取得
   7. `frontend/Dockerfile`(Vite build → nginx配信)をビルドして起動
      (nginxが `/api/*` を、取得したバックエンドIPへプロキシ)

   ※ Apple純正の埋め込みDNS(`*.local`名前解決)は現時点で不安定なことがあるため、
   このスクリプトではDNSに頼らず `container inspect` で取得したIPアドレスを直接環境変数として渡す方式にしています。
   コンテナのIPアドレスは再起動すると変わることがあるので、再起動する場合は`down`してから改めて`up`してください。

3. ブラウザで開く

   **必ず `http://127.0.0.1:5173` を使ってください**(`localhost`ではCookie認証が失敗します。理由はルートの`README.md`を参照)。
   バックエンドのSwagger UIは `http://127.0.0.1:8000/docs` です。

## CLI版を使う場合

スクリプトはDBのポートをホストの`127.0.0.1:5432`に公開しているので、CLIはホスト側で実行できます。
`backend/.env`の`DATABASE_URL`をその宛先にしてください。手順は`backend/README.md`を参照してください。

## 停止・ログ確認

```bash
./scripts/run-apple-container.sh logs backend   # backend / frontend / db
./scripts/run-apple-container.sh down           # コンテナを停止・削除(ネットワークは残す)
```
