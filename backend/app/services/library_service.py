"""プレイリスト一覧取得・ライブラリ同期のコアロジック。

api/(FastAPI) と cli/ の両方から呼ばれる、HTTP層に依存しないビジネスロジック。
"""

import logging
from typing import Any

from spotipy.exceptions import SpotifyException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Track, TrackPlaylistMembership, User
from app.schemas import PlaylistOut, SyncResultOut
from app.services import spotify_client
from app.services.user_service import get_valid_access_token

logger = logging.getLogger(__name__)

LIKED_SONGS_ID = "liked_songs"
LIKED_SONGS_NAME = "お気に入り曲 (Liked Songs)"


def _is_fetchable(playlist: dict[str, Any], own_spotify_user_id: str) -> bool:
    """Spotify APIの仕様上、プレイリストの中身(曲一覧)を取得できるのは
    「自分が所有しているプレイリスト」か「自分がコラボレーターのプレイリスト」だけ。
    それ以外(フォローしているだけの他人のプレイリストや、Spotifyのおまかせ系)は
    401/403になるため、選択肢に出す前に除外する。
    """
    owner_id = (playlist.get("owner") or {}).get("id")
    if owner_id == own_spotify_user_id:
        return True
    return bool(playlist.get("collaborative"))


def get_selectable_playlists(db: Session, user: User) -> list[PlaylistOut]:
    """同期対象として選べるプレイリスト一覧を返す。

    先頭に「お気に入り曲(Liked Songs)」を疑似プレイリストとして含める。
    中身を取得できない(自分の所有でもコラボレーターでもない)プレイリストは
    そもそも一覧に出さない。
    """
    access_token = get_valid_access_token(db, user)

    liked_total = spotify_client.fetch_saved_tracks_total(access_token)
    result = [
        PlaylistOut(
            id=LIKED_SONGS_ID,
            name=LIKED_SONGS_NAME,
            image_url=None,
            track_count=liked_total,
            is_liked_songs=True,
        )
    ]

    for p in spotify_client.fetch_current_user_playlists(access_token):
        try:
            if not _is_fetchable(p, user.spotify_user_id):
                continue
            images = p.get("images") or []
            result.append(
                PlaylistOut(
                    id=p["id"],
                    name=p.get("name", "(無題のプレイリスト)"),
                    image_url=images[0]["url"] if images else None,
                    track_count=(p.get("tracks") or {}).get("total", 0),
                    is_liked_songs=False,
                )
            )
        except Exception as e:  # 想定外の形のプレイリストが来ても一覧取得自体は継続する
            logger.warning("プレイリスト情報の解析に失敗しました: %s (%s)", p.get("id"), e)
            continue

    return result


def _upsert_tracks(db: Session, payloads: list[dict[str, Any]]) -> dict[str, Track]:
    """トラックをまとめてupsertし、spotify_track_id -> Track の辞書を返す。

    曲ごとに個別SELECTすると件数分のクエリが飛ぶため(N+1)、
    既存分を1回のIN句でまとめて引いてから差分だけINSERTする。
    """
    spotify_ids = [p["spotify_track_id"] for p in payloads]
    if not spotify_ids:
        return {}

    existing = {
        t.spotify_track_id: t
        for t in db.query(Track).filter(Track.spotify_track_id.in_(spotify_ids)).all()
    }

    for payload in payloads:
        track = existing.get(payload["spotify_track_id"])
        if track is None:
            track = Track(**payload)
            db.add(track)
            existing[payload["spotify_track_id"]] = track
        else:
            # メタ情報(曲名・アーティスト・画像)が変わっている可能性があるので追随する
            for key, value in payload.items():
                if key != "spotify_track_id":
                    setattr(track, key, value)

    db.flush()  # 新規Trackのidを確定させる
    return existing


def _upsert_memberships(
    db: Session,
    user_id: int,
    playlist_id: str,
    playlist_name: str,
    tracks: list[Track],
) -> tuple[int, int]:
    """プール(プレイリスト)への所属をまとめてupsertし、(新規, 既存) の件数を返す。

    新規に追加された曲だけ初期レーティングで作成し、既にこのプールにある曲は
    再同期してもレート・対戦回数を維持する。
    """
    track_ids = [t.id for t in tracks]
    if not track_ids:
        return 0, 0

    existing = {
        m.track_id: m
        for m in db.query(TrackPlaylistMembership)
        .filter(
            TrackPlaylistMembership.user_id == user_id,
            TrackPlaylistMembership.playlist_id == playlist_id,
            TrackPlaylistMembership.track_id.in_(track_ids),
        )
        .all()
    }

    created = 0
    updated = 0

    for track in tracks:
        membership = existing.get(track.id)
        if membership is None:
            db.add(
                TrackPlaylistMembership(
                    user_id=user_id,
                    track_id=track.id,
                    playlist_id=playlist_id,
                    playlist_name=playlist_name,
                    rating=settings.elo_initial_rating,
                    match_count=0,
                )
            )
            created += 1
        else:
            if membership.playlist_name != playlist_name:
                membership.playlist_name = playlist_name
            updated += 1

    return created, updated


def sync_playlists(
    db: Session,
    user: User,
    playlist_ids: list[str],
    playlist_names: dict[str, str] | None = None,
) -> SyncResultOut:
    """選択されたプレイリスト(未指定ならLiked Songs)を取得し、
    tracks / track_playlist_memberships へ反映する。

    playlist_names に「プレイリストid -> 表示名」を渡すと、Spotifyへの
    一覧再取得を省略できる(呼び出し側は選択時に一覧を持っているため)。

    一部のプレイリストの取得に失敗しても、他のプレイリストの同期は継続し、
    失敗したものは SyncResultOut.skipped_playlist_ids に含める。
    呼び出し側が db.commit() する前提(この関数自体はcommitしない)。
    """
    access_token = get_valid_access_token(db, user)
    playlist_ids = playlist_ids or [LIKED_SONGS_ID]

    name_map: dict[str, str] = {LIKED_SONGS_ID: LIKED_SONGS_NAME, **(playlist_names or {})}
    # 呼び出し側から名前が渡っていないものがある場合のみ、Spotifyから一覧を取り直す
    if any(pid not in name_map for pid in playlist_ids):
        for p in spotify_client.fetch_current_user_playlists(access_token):
            name_map.setdefault(p["id"], p.get("name", "(無題のプレイリスト)"))

    total_fetched = 0
    total_created = 0
    total_updated = 0
    skipped: list[str] = []

    for playlist_id in playlist_ids:
        try:
            if playlist_id == LIKED_SONGS_ID:
                payloads = spotify_client.fetch_all_saved_tracks(access_token)
            else:
                payloads = spotify_client.fetch_playlist_tracks(access_token, playlist_id)
        except SpotifyException as e:
            # 所有・コラボレーターでないプレイリストなど、取得できないものはスキップして続行する
            logger.warning("プレイリスト %s の取得に失敗しました: %s", playlist_id, e)
            skipped.append(playlist_id)
            continue

        total_fetched += len(payloads)

        # 同一プレイリスト内に同じ曲が重複していても1件として扱う
        unique_payloads = list({p["spotify_track_id"]: p for p in payloads}.values())

        track_map = _upsert_tracks(db, unique_payloads)
        tracks = [track_map[p["spotify_track_id"]] for p in unique_payloads]

        created, updated = _upsert_memberships(
            db, user.id, playlist_id, name_map.get(playlist_id, playlist_id), tracks
        )
        total_created += created
        total_updated += updated

    return SyncResultOut(
        fetched=total_fetched,
        created=total_created,
        updated=total_updated,
        skipped_playlist_ids=skipped,
    )
