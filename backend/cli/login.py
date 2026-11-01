"""Spotify OAuthでログインし、ログイン中ユーザーをローカルに記録する。

使い方:
    python -m cli.login

ブラウザでSpotifyの認可画面が開くので許可すると、ローカルに一時的に立てた
HTTPサーバーがコールバックを受け取り、トークン交換・ユーザー登録まで行う。
"""

import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from cli._session import db_session, save_session
from app.config import settings
from app.services import spotify_client, user_service

_received: dict[str, str] = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.serverの命名規則に合わせる)
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            _received["code"] = query["code"][0]
            body = "認証が完了しました。このタブは閉じてターミナルに戻ってください。"
        elif "error" in query:
            _received["error"] = query["error"][0]
            body = f"認証がキャンセル/失敗しました: {query['error'][0]}"
        else:
            body = "不明なリクエストです。"

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # 標準のアクセスログは出さない


def _wait_for_callback(port: int) -> str:
    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    server.timeout = 180  # 秒。ブラウザ操作を待つのでやや長め
    print("ブラウザでの認可待ち... (3分でタイムアウトします)")
    server.handle_request()
    server.server_close()

    if "error" in _received:
        print(f"認証エラー: {_received['error']}")
        sys.exit(1)
    if "code" not in _received:
        print("タイムアウトしました。もう一度 `python -m cli.login` を実行してください。")
        sys.exit(1)

    return _received["code"]


def main() -> None:
    redirect_uri = settings.spotify_cli_redirect_uri
    port = urlparse(redirect_uri).port or 8765

    authorize_url = spotify_client.get_authorize_url(redirect_uri)
    print(f"ブラウザを開きます。開かない場合は以下のURLにアクセスしてください:\n{authorize_url}\n")
    webbrowser.open(authorize_url)

    code = _wait_for_callback(port)

    token_info = spotify_client.exchange_code_for_token(code, redirect_uri)

    with db_session() as db:
        user = user_service.upsert_user_from_token(db, token_info)
        db.commit()
        save_session(user.id)
        print(f"ログインしました: {user.display_name or user.spotify_user_id}")


if __name__ == "__main__":
    main()
