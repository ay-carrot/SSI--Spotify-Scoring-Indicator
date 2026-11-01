from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.security import get_current_user_id
from app.db_session import get_db
from app.schemas import RankedTrackOut, RankingFilterOut
from app.services import battle_service

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("", response_model=list[RankedTrackOut])
def get_rankings(
    playlist_id: str = Query(..., description="表示するプール(プレイリスト)のid"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[RankedTrackOut]:
    """指定プール(プレイリスト)内のレーティング順ランキングを返す。

    レーティングはプールごとに独立しているため、必ずどのプールを見るか指定する。
    """
    return battle_service.get_pool_rankings(db, user_id, playlist_id, limit, offset)


@router.get("/filters", response_model=list[RankingFilterOut])
def get_ranking_filters(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[RankingFilterOut]:
    """ランキング・対戦画面で選べるプール(同期済みプレイリスト)の一覧。"""
    return battle_service.get_pools(db, user_id)
