from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- ユーザー ---


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spotify_user_id: str
    display_name: str | None
    email: str | None


# --- トラック ---


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spotify_track_id: str
    name: str
    artist_name: str
    image_url: str | None


class RankedTrackOut(TrackOut):
    rating: float
    match_count: int


class PairOut(BaseModel):
    track_a: RankedTrackOut
    track_b: RankedTrackOut


# --- 対戦結果 ---

MatchResult = Literal["a_win", "b_win", "draw"]


class MatchIn(BaseModel):
    playlist_id: str
    track_a_id: int
    track_b_id: int
    result: MatchResult


class MatchOut(BaseModel):
    track_a: RankedTrackOut
    track_b: RankedTrackOut
    result: MatchResult


# --- ライブラリ同期 ---


class PlaylistOut(BaseModel):
    id: str
    name: str
    image_url: str | None
    track_count: int
    is_liked_songs: bool = False


class SyncIn(BaseModel):
    # 空/未指定なら「お気に入り曲(Liked Songs)」のみを同期する。
    # "liked_songs" という特別なIDを含めることもできる。
    playlist_ids: list[str] = Field(default_factory=list)


class SyncResultOut(BaseModel):
    fetched: int
    created: int
    updated: int
    skipped_playlist_ids: list[str] = Field(default_factory=list)


class RankingFilterOut(BaseModel):
    """ランキング画面の絞り込み選択肢(実際に同期済みのプレイリストのみ)。"""

    playlist_id: str
    playlist_name: str
    track_count: int
