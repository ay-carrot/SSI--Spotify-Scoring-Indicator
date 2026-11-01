# SSI - Frontend (Vue 3 + TypeScript)

Vue 3 + TypeScript + Vite によるWeb画面です。画面表示だけを担当し、
Spotify連携・DB設計・Eloロジックはすべてバックエンド側(`backend/`)にあります。
全体構成・セットアップ・Docker Composeなどでの一括起動は、リポジトリルートの[`README.md`](../README.md)を参照してください。

## 開発サーバーの起動

前提: バックエンドが `http://127.0.0.1:8000` で起動していること。

```bash
cd frontend
npm install       # 初回のみ
npm run dev
```

`http://127.0.0.1:5173` で起動します。`/api` へのリクエストは`vite.config.ts`の設定により、
`http://127.0.0.1:8000`(バックエンド)へプロキシされます。

**`localhost`ではなく、必ず`127.0.0.1`でアクセスしてください**(`localhost`ではCookie認証が効きません。理由はルートの`README.md`を参照)。

## 画面構成

- `/` : ログイン画面(Spotify OAuth開始)
- `/battle` : 対戦画面(2曲を提示し、好きな方を選ぶ)
- `/rankings` : Eloレーティング順のランキング一覧

## 実装上の注意

- 認証はバックエンドが発行するhttpOnly Cookieで管理しているため、`fetch`には`credentials: "include"`を必ず付与しています(`src/api/client.ts`)。

## コンテナでの配信

`frontend/Dockerfile`は、Viteでビルドした静的ファイルをnginxで配信します。
nginxは`/api/*`を、環境変数`BACKEND_HOST`・`BACKEND_PORT`で指定されたバックエンドへプロキシします
(Docker Composeでは`backend:8000`、Apple containerではバックエンドコンテナのIPアドレス)。
