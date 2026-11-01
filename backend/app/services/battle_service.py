"""対戦・ランキングのコアロジック(Eloレーティング計算を含む)。

api/(FastAPI) と cli/ の両方から呼ばれる、HTTP層に依存しないビジネスロジック。
エラーは app.exceptions の例外で表現し、呼び出し側がそれぞれの形式に変換する。
"""

import random

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import NotFoundError, ValidationError
from app.models import TrackPlaylistMembership
from app.schemas import MatchOut, MatchResult, PairOut, RankedTrackOut, RankingFilterOut

# 対戦ペア選定の候補プール(対戦回数が少ない順に、この件数だけ取り出す)
CANDIDATE_POOL_SIZE = 30
# レーティングが近い相手を選ぶ際に、上位何件からランダムに選ぶか
CLOSE_RATING_SAMPLE = 5

# track_a から見た実際のスコア S。引き分けは0.5とする標準的なElo定義。
_SCORE_A: dict[str, float] = {"a_win": 1.0, "b_win": 0.0, "draw": 0.5}


# --- Eloレーティング ---


def _k_factor(match_count: int) -> float:
    """対戦回数が少ないほどレートを大きく動かし、初期の収束を早める(プロビジョナル期間)。"""
    if match_count < 5:
        return settings.elo_k_factor * 2
    if match_count < 15:
        return settings.elo_k_factor * 1.5
    return settings.elo_k_factor


def update_ratings(
    rating_a: float,
    rating_b: float,
    match_count_a: int,
    match_count_b: int,
    result: MatchResult,
) -> tuple[float, float]:
    """対戦結果(勝ち/負け/引き分け)を反映した新しいレーティングのペアを返す。

    新レート = 現レート + K × (S − E)
    S = 実際のスコア(勝ち1.0 / 引き分け0.5 / 負け0.0)、E = 期待勝率。
    引き分けも同じ式に乗るため、格上に引き分けた格下はレートが上がり、
    格下に引き分けた格上はレートが下がる。
    """
    score_a = _SCORE_A[result]
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    new_rating_a = rating_a + _k_factor(match_count_a) * (score_a - expected_a)
    # B側は S_b = 1 - S_a、E_b = 1 - E_a なので、S_b - E_b = E_a - S_a
    new_rating_b = rating_b + _k_factor(match_count_b) * (expected_a - score_a)

    return new_rating_a, new_rating_b


# --- 対戦 ---


def _to_ranked(membership: TrackPlaylistMembership) -> RankedTrackOut:
    return RankedTrackOut.model_validate(
        {**membership.track.__dict__, "rating": membership.rating, "match_count": membership.match_count}
    )


def get_battle_pair(db: Session, user_id: int, playlist_id: str) -> PairOut:
    """指定したプール(プレイリスト)内で対戦させる2曲を選んで返す。

    対戦は常に1プール内で完結し、プールをまたいだ対戦は行わない
    (曲ごとにプール単位で独立したレーティングを持つため)。
    対戦回数が少ない曲を優先しつつ、レーティングが近い相手とぶつけることで
    Eloレーティングの収束を早める。

    Raises:
        ValidationError: このプールに対戦可能な曲(2曲以上)が無い場合。
    """
    pool = (
        db.query(TrackPlaylistMembership)
        .filter(
            TrackPlaylistMembership.user_id == user_id,
            TrackPlaylistMembership.playlist_id == playlist_id,
        )
        .order_by(TrackPlaylistMembership.match_count.asc(), func.random())
        .limit(CANDIDATE_POOL_SIZE)
        .all()
    )

    if len(pool) < 2:
        raise ValidationError(
            "このプールには対戦可能な曲が不足しています。先にライブラリを同期してください。"
        )

    track_a = random.choice(pool)
    rest = [m for m in pool if m.id != track_a.id]
    rest.sort(key=lambda m: abs(m.rating - track_a.rating))
    track_b = random.choice(rest[:CLOSE_RATING_SAMPLE])

    return PairOut(track_a=_to_ranked(track_a), track_b=_to_ranked(track_b))


def submit_match(
    db: Session,
    user_id: int,
    playlist_id: str,
    track_a_id: int,
    track_b_id: int,
    result: MatchResult,
) -> MatchOut:
    """指定プール内での対戦結果(track_aの勝ち/track_bの勝ち/引き分け)を受け取り、
    そのプール内でのEloレーティングを更新する。
    呼び出し側が db.commit() する前提(この関数自体はcommitしない)。

    Raises:
        ValidationError: 同じ曲同士を指定した場合。
        NotFoundError: 対象の曲がこのプールに無い場合。
    """
    if track_a_id == track_b_id:
        raise ValidationError("同じ曲同士は対戦できません")

    # 2曲まとめて1回のクエリで引く
    memberships = {
        m.track_id: m
        for m in db.query(TrackPlaylistMembership)
        .filter(
            TrackPlaylistMembership.user_id == user_id,
            TrackPlaylistMembership.playlist_id == playlist_id,
            TrackPlaylistMembership.track_id.in_([track_a_id, track_b_id]),
        )
        .all()
    }

    m_a = memberships.get(track_a_id)
    m_b = memberships.get(track_b_id)
    if m_a is None or m_b is None:
        raise NotFoundError("対象の曲がこのプールに見つかりません")

    new_rating_a, new_rating_b = update_ratings(
        m_a.rating, m_b.rating, m_a.match_count, m_b.match_count, result
    )

    m_a.rating = new_rating_a
    m_a.match_count += 1
    m_b.rating = new_rating_b
    m_b.match_count += 1

    db.flush()

    return MatchOut(track_a=_to_ranked(m_a), track_b=_to_ranked(m_b), result=result)


# --- ランキング ---


def get_pools(db: Session, user_id: int) -> list[RankingFilterOut]:
    """ランキング・対戦で選べるプール(同期済みプレイリスト)の一覧。"""
    rows = (
        db.query(
            TrackPlaylistMembership.playlist_id,
            TrackPlaylistMembership.playlist_name,
            func.count(TrackPlaylistMembership.id).label("track_count"),
        )
        .filter(TrackPlaylistMembership.user_id == user_id)
        .group_by(TrackPlaylistMembership.playlist_id, TrackPlaylistMembership.playlist_name)
        .order_by(TrackPlaylistMembership.playlist_name.asc())
        .all()
    )

    return [
        RankingFilterOut(playlist_id=r.playlist_id, playlist_name=r.playlist_name, track_count=r.track_count)
        for r in rows
    ]


def get_pool_rankings(
    db: Session, user_id: int, playlist_id: str, limit: int = 50, offset: int = 0
) -> list[RankedTrackOut]:
    """指定プール(プレイリスト)内のレーティング順ランキングを返す。"""
    memberships = (
        db.query(TrackPlaylistMembership)
        .filter(
            TrackPlaylistMembership.user_id == user_id,
            TrackPlaylistMembership.playlist_id == playlist_id,
        )
        .order_by(TrackPlaylistMembership.rating.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_to_ranked(m) for m in memberships]
