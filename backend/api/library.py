from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.security import get_current_user
from app.db_session import get_db
from app.models import User
from app.schemas import PlaylistOut, SyncIn, SyncResultOut
from app.services import library_service

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/playlists", response_model=list[PlaylistOut])
def list_playlists(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlaylistOut]:
    return library_service.get_selectable_playlists(db, user)


@router.post("/sync", response_model=SyncResultOut)
def sync_library(
    payload: SyncIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyncResultOut:
    result = library_service.sync_playlists(db, user, payload.playlist_ids)
    db.commit()
    return result
