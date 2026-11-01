"""Spotipyを利用したSpotify連携。

トークンの永続化はこちらでは行わず、呼び出し側(user_service・api.auth など)が
DBへの保存・復号を担当する。ここではSpotify Web APIとのやり取りと、
トラック情報をアプリ内部の形(辞書)へ正規化するところまでを担当する。
Spotify側の仕様変更の影響は、このファイルに閉じ込める。
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app.config import settings


def _get_oauth_manager(redirect_uri: str | None = None) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        redirect_uri=redirect_uri or settings.spotify_redirect_uri,
        scope=settings.spotify_scopes,
        # spotipy標準のファイルキャッシュは使わず、こちらでDB管理する
        cache_handler=spotipy.MemoryCacheHandler(),
        show_dialog=False,
    )


def get_authorize_url(redirect_uri: str | None = None) -> str:
    return _get_oauth_manager(redirect_uri).get_authorize_url()


def exchange_code_for_token(code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    """認可コードをアクセストークン/リフレッシュトークンに交換する。

    redirect_uri は、CLIなどWeb版と異なるコールバック先を使う場合に指定する
    (Spotifyは認可リクエスト時とトークン交換時でredirect_uriの一致を要求するため)。
    """
    return _get_oauth_manager(redirect_uri).get_access_token(code, as_dict=True, check_cache=False)


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    return _get_oauth_manager().refresh_access_token(refresh_token)


def expires_at_from_expires_in(expires_in: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=expires_in)


def fetch_current_user_profile(access_token: str) -> dict[str, Any]:
    return spotipy.Spotify(auth=access_token).current_user()


def _paginate(fetch_page: Callable[[int, int], dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """fetch_page(limit, offset) を、最後のページまで繰り返し呼んでitemsを連結する。"""
    items: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = fetch_page(limit, offset)
        page_items = page.get("items", [])
        if not page_items:
            break
        items.extend(page_items)
        if page.get("next") is None:
            break
        offset += limit
    return items


def _extract_track(item: dict[str, Any]) -> dict[str, Any] | None:
    """保存済み曲/プレイリストアイテム1件から、DB保存に必要な情報を取り出す。

    保存対象外(ローカルファイル、取得できないトラック)の場合は None を返す。
    """
    # ローカルファイル(is_local)は、内側のtrack/itemオブジェクトではなく
    # 外側のitem直下にフラグが付く仕様なのでここで弾く。
    if item.get("is_local"):
        return None

    # Spotifyの2026年2月API変更で、プレイリストアイテムのtrack情報が
    # "track"キーから"item"キーに変わった(エンドポイントも/tracks→/itemsに変更)。
    # spotipy 2.26.0はエンドポイント自体は追随したが、辞書のキー名までは
    # 旧キーに正規化していないため、新旧どちらのキーにも対応しておく。
    t = item.get("track") or item.get("item")
    if t is None or t.get("id") is None or t.get("is_local"):
        return None

    images = (t.get("album") or {}).get("images") or []
    return {
        "spotify_track_id": t["id"],
        "name": t["name"],
        "artist_name": ", ".join(a["name"] for a in t.get("artists", [])),
        "image_url": images[0]["url"] if images else None,
    }


def fetch_all_saved_tracks(access_token: str) -> list[dict[str, Any]]:
    """Liked Songsを全件取得し、正規化済みのトラック情報(辞書)のリストで返す。"""
    sp = spotipy.Spotify(auth=access_token)
    items = _paginate(lambda limit, offset: sp.current_user_saved_tracks(limit=limit, offset=offset), 50)
    return [t for item in items if (t := _extract_track(item))]


def fetch_playlist_tracks(access_token: str, playlist_id: str) -> list[dict[str, Any]]:
    """指定プレイリストの曲を全件取得し、正規化済みのトラック情報(辞書)のリストで返す。

    ローカルファイルや配信停止曲など、取り出せなかったアイテムは除外される。
    """
    sp = spotipy.Spotify(auth=access_token)
    items = _paginate(
        lambda limit, offset: sp.playlist_items(
            playlist_id, limit=limit, offset=offset, additional_types=("track",)
        ),
        100,
    )
    return [t for item in items if (t := _extract_track(item))]


def fetch_saved_tracks_total(access_token: str) -> int:
    """保存済み曲(Liked Songs)の総数のみを軽量に取得する。"""
    return spotipy.Spotify(auth=access_token).current_user_saved_tracks(limit=1).get("total", 0)


def fetch_current_user_playlists(access_token: str) -> list[dict[str, Any]]:
    """ユーザーが持つ(フォロー含む)プレイリストを全件取得する。"""
    sp = spotipy.Spotify(auth=access_token)
    return _paginate(lambda limit, offset: sp.current_user_playlists(limit=limit, offset=offset), 50)
