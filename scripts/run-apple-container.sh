#!/usr/bin/env bash
# Apple の `container` CLI で SSI (Spotify Elo) を一括起動するスクリプト。
#
# 埋め込みDNS(*.local など)はまだ不安定なことがあるため、コンテナ間の通信は
# `container inspect` で取得した各コンテナのIPアドレスを直接渡す方式にしている。
#
# 前提:
#   - Apple Silicon Mac, macOS 26 (Tahoe) 推奨
#     (macOS 15 でも動くがコンテナ間ネットワークに制限あり)
#   - `container` CLI インストール済み (brew install --cask container、
#     もしくは https://github.com/apple/container の .pkg)
#   - backend/.env を用意済み (無ければ backend/.env.example からコピーして
#     SPOTIFY_CLIENT_ID などを埋めてください)
#   - python3 がホスト側で使えること (container inspect の出力をパースするため)
#
# 使い方:
#   chmod +x scripts/run-apple-container.sh
#   ./scripts/run-apple-container.sh up      # ビルド & 起動
#   ./scripts/run-apple-container.sh down    # 停止 & 削除
#   ./scripts/run-apple-container.sh logs backend   # ログ表示

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

NETWORK="spotify-elo-net"
DB_NAME="ssi-db"
BACKEND_NAME="ssi-backend"
FRONTEND_NAME="ssi-frontend"

DB_IMAGE="postgres:16"
BACKEND_IMAGE="ssi-backend:latest"
FRONTEND_IMAGE="ssi-frontend:latest"

DB_PORT=5432
BACKEND_PORT=8000
FRONTEND_PORT=5173

need_env_file() {
  if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "backend/.env がありません。backend/.env.example をコピーして"
    echo "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET などを設定してください。"
    exit 1
  fi
}

ensure_system() {
  if ! command -v container >/dev/null 2>&1; then
    echo "container CLI が見つかりません。https://github.com/apple/container からインストールしてください。"
    exit 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 が見つかりません（container inspect の出力パースに使用します）。"
    exit 1
  fi
  container system start >/dev/null 2>&1 || true
}

ensure_network() {
  container network create "$NETWORK" >/dev/null 2>&1 || true
}

# 指定したコンテナのIPv4アドレスを取得する。起動直後はIPがまだ割り当たっていない
# ことがあるため、数秒リトライする。
get_container_ip() {
  local name="$1"
  for _ in $(seq 1 15); do
    local ip
    ip="$(container inspect "$name" 2>/dev/null | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    entry = data[0] if isinstance(data, list) else data
    # "status.networks[].ipv4Address" を優先し、
    # 無ければ念のため configuration.networks 側も見る
    candidates = (entry.get("status") or {}).get("networks") or []
    if not candidates:
        candidates = entry.get("networks") or []
    for net in candidates:
        addr = net.get("ipv4Address") or net.get("address") or ""
        if addr:
            print(addr.split("/")[0])
            break
except Exception:
    pass
' 2>/dev/null)"
    if [ -n "${ip:-}" ]; then
      echo "$ip"
      return 0
    fi
    sleep 1
  done
  echo "エラー: ${name} のIPアドレスを取得できませんでした。'container inspect ${name}' で確認してください。" >&2
  return 1
}

up() {
  need_env_file
  ensure_system
  ensure_network

  echo "==> PostgreSQL を起動"
  container run -d \
    --name "$DB_NAME" \
    --network "$NETWORK" \
    -p "${DB_PORT}:5432" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=spotify_elo \
    "$DB_IMAGE" || echo "  (既に起動済み、またはエラー。'./scripts/run-apple-container.sh down' で一度片付けてください)"

  echo "==> PostgreSQL のIPアドレスを取得"
  DB_IP="$(get_container_ip "$DB_NAME")"
  echo "  DB_IP=${DB_IP}"

  echo "==> PostgreSQL の起動を待機"
  for i in $(seq 1 30); do
    if container exec "$DB_NAME" pg_isready -U postgres >/dev/null 2>&1; then
      echo "  PostgreSQL 準備完了"
      break
    fi
    sleep 1
  done

  echo "==> バックエンドイメージをビルド"
  container build --tag "$BACKEND_IMAGE" --file "$BACKEND_DIR/Dockerfile" "$BACKEND_DIR"

  echo "==> バックエンドを起動"
  container run -d \
    --name "$BACKEND_NAME" \
    --network "$NETWORK" \
    -p "${BACKEND_PORT}:8000" \
    --env-file "$BACKEND_DIR/.env" \
    -e "DATABASE_URL=postgresql+psycopg2://postgres:postgres@${DB_IP}:5432/spotify_elo" \
    "$BACKEND_IMAGE"

  echo "==> バックエンドのIPアドレスを取得"
  BACKEND_IP="$(get_container_ip "$BACKEND_NAME")"
  echo "  BACKEND_IP=${BACKEND_IP}"

  echo "==> バックエンドの起動を待機"
  for i in $(seq 1 20); do
    if container exec "$BACKEND_NAME" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" >/dev/null 2>&1; then
      echo "  バックエンド準備完了"
      break
    fi
    sleep 1
  done

  echo "==> フロントエンドイメージをビルド"
  container build --tag "$FRONTEND_IMAGE" --file "$FRONTEND_DIR/Dockerfile" "$FRONTEND_DIR"

  echo "==> フロントエンドを起動"
  container run -d \
    --name "$FRONTEND_NAME" \
    --network "$NETWORK" \
    -p "${FRONTEND_PORT}:80" \
    -e "BACKEND_HOST=${BACKEND_IP}" \
    -e "BACKEND_PORT=8000" \
    "$FRONTEND_IMAGE"

  cat <<EOF

起動しました。
  フロントエンド: http://127.0.0.1:${FRONTEND_PORT}
  バックエンド:   http://127.0.0.1:${BACKEND_PORT}/docs

Spotify Developer Dashboard の Redirect URI は
  http://127.0.0.1:${BACKEND_PORT}/auth/callback
にしてください（backend/.env の SPOTIFY_REDIRECT_URI と一致させること。
Spotifyはhttpの場合ループバックIPリテラル127.0.0.1のみ許可し、localhostは拒否します）。
※ Cookie認証のため、フロントエンド側も "127.0.0.1" で開いてください
  （"localhost" でアクセスするとCookieが共有されず401になります）。
  → http://127.0.0.1:${FRONTEND_PORT}

注意: コンテナのIPアドレスは再起動すると変わることがあります。
再起動する場合は down してから改めて up してください。
EOF
}

down() {
  for name in "$FRONTEND_NAME" "$BACKEND_NAME" "$DB_NAME"; do
    container stop "$name" >/dev/null 2>&1 || true
    container rm "$name" >/dev/null 2>&1 || true
  done
  echo "停止・削除しました（ネットワークは残しています）。"
}

logs() {
  local target="${1:-backend}"
  case "$target" in
    backend) container logs -f "$BACKEND_NAME" ;;
    frontend) container logs -f "$FRONTEND_NAME" ;;
    db) container logs -f "$DB_NAME" ;;
    *) echo "logs の対象は backend / frontend / db のいずれかを指定してください" ;;
  esac
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  logs) logs "${2:-}" ;;
  *)
    echo "使い方: $0 {up|down|logs [backend|frontend|db]}"
    exit 1
    ;;
esac
