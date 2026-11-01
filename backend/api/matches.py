from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.security import get_current_user_id
from app.db_session import get_db
from app.schemas import MatchIn, MatchOut, PairOut
from app.services import battle_service

router = APIRouter(tags=["matches"])


@router.get("/tracks/pair", response_model=PairOut)
def get_pair(
    playlist_id: str = Query(..., description="対戦を行うプール(プレイリスト)のid"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PairOut:
    return battle_service.get_battle_pair(db, user_id, playlist_id)


@router.post("/matches", response_model=MatchOut)
def create_match(
    payload: MatchIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MatchOut:
    result = battle_service.submit_match(
        db, user_id, payload.playlist_id, payload.track_a_id, payload.track_b_id, payload.result
    )
    db.commit()
    return result
