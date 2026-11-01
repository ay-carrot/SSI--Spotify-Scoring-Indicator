# Spotify Scoring Indicator (SSI)

このアプリケーションはPython初学者の私ががポートフォリオとして作成したアプリケーションです。
私の環境(M3 Mac / Apple Container)では問題なく動作しておりますが、他環境での動作の保証は致しかねます。
フロントエンドの実装については知識不足のためほぼAIによるものです。ご了承ください。

Spotifyの保存済みライブラリを取得し、2曲を比較させることでEloレーティングを算出するアプリケーションです。
ブラウザで使うWeb版と、ターミナルで完結するCLI版があり、どちらも同じDB・同じコアロジック(`backend/app/services/`)を共有しています。

| 構成要素 | 技術 | 場所 |
|---|---|---|
| バックエンド(Web API) | FastAPI + Spotipy + PostgreSQL | `backend/api/` + `backend/app/` |
| フロントエンド | Vue 3 + TypeScript + Vite | `frontend/` |
| CLI | 共有コアを直接呼ぶ、ターミナル版 | `backend/cli/` |

## 目次

- [ドキュメント](#ドキュメント)
- [全体構成](#全体構成)
- [コード構成](#コード構成)
- [セットアップ](#セットアップ)
- [起動](#起動)
- [補足](#補足)

## ドキュメント

| ファイル | 内容 |
|---|---|
| `README.md`(このファイル) | 全体構成、セットアップ、起動方法、仕様 |
| `backend/README.md` | API一覧、CLIの使い方、テスト |
| `frontend/README.md` | フロントエンドの開発サーバー、画面構成 |
| `APPLE_CONTAINER.md` | Apple `container` CLI での起動手順 |
| `docker-compose.yml` | Docker Compose での起動定義(使い方は冒頭のコメント) |

## 全体構成

```
[Vue Frontend]
      │
      │  REST API(Cookie: JWTセッション)
      ▼
[FastAPI (api/)]                      [CLI (cli/)]
      │                                    │
      └─────────────────┬──────────────────┘
                        │  関数呼び出し(同一プロセス内)
                        ▼
        [共有コア (app/): services / models / schemas]
              │                       │
              ▼                       ▼
        [PostgreSQL]            [Spotify Web API]
                                (OAuth + データ取得)
```

- `api/`と`cli/`はどちらも、`app/services/`のコアロジックを呼び出すだけの入口です。
- 依存の向きは常に `api/` → `app/` ← `cli/` で、`api/`と`cli/`が互いに依存することはありません。
- Web版のログインはCookie(JWT)、CLI版のログインはローカルファイルで、互いに独立しています。

## コード構成

### リポジトリ全体

```
.
├─ backend/                FastAPI・CLI・共有コア(下記)
├─ frontend/               Vue 3 + TypeScript + Vite
├─ scripts/
│   └─ run-apple-container.sh   Apple container で一括起動
├─ docker-compose.yml      Docker Compose で一括起動
├─ APPLE_CONTAINER.md
└─ README.md
```

### backend/

```
backend/
├─ app/                     共有コア(api/・cli/どちらからも使う)
│   ├─ config.py            設定(.envの読み込み)
│   ├─ exceptions.py        アプリ共通の例外(api/はHTTPException、cli/はメッセージ表示に変換)
│   ├─ db_session.py        Base・engine・セッション(get_db)
│   ├─ models.py            DBモデル(User / Track / TrackPlaylistMembership)
│   ├─ schemas.py           入出力の型(Pydantic)
│   └─ services/            HTTP・CLIに依存しない実処理
│       ├─ spotify_client.py   Spotify Web API連携。トラック情報の正規化もここで行い、API仕様変更の影響をこのファイルに閉じ込める
│       ├─ user_service.py     Spotifyトークンの暗号化/復号、OAuth後のユーザー作成・更新、アクセストークンの更新
│       ├─ library_service.py  プレイリスト一覧の取得、ライブラリ同期
│       └─ battle_service.py   対戦ペア選出、対戦結果の反映、Elo計算、プール一覧・ランキング
├─ api/                     FastAPI専用
│   ├─ main.py              起動エントリーポイント
│   ├─ security.py          JWT/Cookieセッション、ログイン中ユーザーの解決(get_current_user)
│   └─ auth.py / library.py / matches.py / rankings.py   ルーター
└─ cli/                     CLI専用
    ├─ main.py              メニュー形式のエントリーポイント
    ├─ _session.py          ログイン状態の保存、DBセッション、番号選択UIの共通部品
    └─ login.py / sync.py / battle.py / rankings.py   各コマンド
```

`app/services/`内の依存は `library_service` → `user_service` → `spotify_client` の一方向で、
`battle_service`は他のサービスに依存しません。

## セットアップ

コンテナ(Docker Compose / Apple container)で動かす場合は、**手順1と2だけ**で済みます(3〜5は不要)。

### 1. Spotify Developer Dashboardでアプリ登録

https://developer.spotify.com/dashboard で新しいアプリを作成し、Client ID / Client Secret を控えます。
Redirect URI には以下を登録します。

| 用途 | Redirect URI |
|---|---|
| Web版 | `http://127.0.0.1:8000/auth/callback` |
| CLI版(使う場合のみ・Web版とは**別に追加**) | `http://127.0.0.1:8765/callback` |

CLI側のポートを変えたい場合は`.env`の`SPOTIFY_CLI_REDIRECT_URI`を書き換え、Dashboard側もそれに合わせてください。

> **`localhost`ではなく、必ず`127.0.0.1`を使ってください。**
> Spotifyはhttpの場合ループバックIPリテラル`127.0.0.1`のみ許可し、`localhost`は拒否します。
> また、Cookieはホスト名単位で共有され、`localhost`と`127.0.0.1`は別ホスト扱いのため、
> フロントエンド(`http://127.0.0.1:5173`)も同じ表記で開かないと認証が401になります。

### 2. 環境変数(`backend/.env`)

```bash
cp backend/env_sample backend/.env
```

`backend/.env`を開き、次の必須項目を設定します。

| 変数 | 内容 |
|---|---|
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | 手順1で控えた値 |
| `DATABASE_URL` | 例: `postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/spotify_elo` |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` で生成 |
| `TOKEN_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` で生成 |

次の項目は任意です(未設定なら括弧内の値)。

`SPOTIFY_REDIRECT_URI`(`http://127.0.0.1:8000/auth/callback`)、
`SPOTIFY_CLI_REDIRECT_URI`(`http://127.0.0.1:8765/callback`)、
`FRONTEND_URL`(`http://127.0.0.1:5173`)、
`JWT_EXPIRE_MINUTES`(`10080` = 7日)、
`ELO_K_FACTOR`(`32`)、`ELO_INITIAL_RATING`(`1500`)

`DATABASE_URL`は、ホスト上で直接動かすバックエンドとCLIがこの値を使います。
Docker Compose / Apple container のバックエンドコンテナは、起動時にDBコンテナ宛ての値で自動的に上書きされます。
コンテナで動かしている場合も、ホスト側のCLIから接続できるよう`127.0.0.1:5432`宛てにしておいてください。

### 3. PostgreSQLを用意

```bash
createdb spotify_elo
```

### 4. Python環境構築

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip              # 新しいPythonのwheelタグを正しく認識させるため
pip install -r requirements.txt        # Web版 + CLI版
# CLI版しか使わない場合は、API専用パッケージ(fastapi/uvicorn/python-jose/httpx/alembic)を含まない軽量版:
# pip install -r requirements-cli.txt
```

### 5. Node環境構築(Web版を使う場合)

```bash
cd frontend
npm install
```

## 起動

### ローカル(Python/Nodeを直接起動)

```bash
# ターミナル1: バックエンド (http://127.0.0.1:8000)
cd backend && source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# ターミナル2: フロントエンド (http://127.0.0.1:5173)
cd frontend
npm run dev
```

ブラウザで `http://127.0.0.1:5173` を開き、「Spotifyでログインして開始」を押します。
初回起動時にテーブルが自動作成されます。

### Docker Compose

```bash
docker compose up -d --build
docker compose logs -f backend      # backend / frontend / db
docker compose down                 # DBのデータは残る(-v を付けると削除)
```

詳細は`docker-compose.yml`冒頭のコメントを参照してください。

### Apple container

```bash
./scripts/run-apple-container.sh up
```

手順の詳細は`APPLE_CONTAINER.md`を参照してください。

### CLI版

```bash
cd backend
python -m cli.main
```

CLIの使い方は`backend/README.md`を参照してください。
コンテナで動かしている場合も、CLIはコンテナの中ではなく**ホスト側で**実行します
(ログイン時のコールバックを、ホストのブラウザからCLIの一時サーバーで受けるため)。

## 補足

### データモデル

| テーブル | 役割 |
|---|---|
| `users` | Spotifyユーザー情報 + 暗号化済みトークン |
| `tracks` | 曲マスタ(全ユーザー共有) |
| `track_playlist_memberships` | ユーザー×曲×プール(プレイリスト)単位のEloレーティング・対戦回数。**レーティングの実体はここ** |

対戦は常に1プール(プレイリスト)単位で行い、同じ曲でも所属プレイリストごとに独立したレートを持ちます。

### Eloレーティングの仕様

実装は`backend/app/services/battle_service.py`です。

- 初期レーティング: 1500
- Kファクター: 対戦回数が少ないうちは大きく変動させて収束を早める(5戦未満はK=64、15戦未満はK=48、以降K=32)
- 勝ち/負け/引き分け(S=1/0/0.5)に対応した標準的なElo定義
- 対戦ペアは「対戦回数が少ない曲」を優先しつつ、「レーティングが近い曲」同士をぶつけて、情報量の多い対戦を優先する
