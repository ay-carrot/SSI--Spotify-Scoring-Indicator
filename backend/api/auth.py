from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from api.security import create_access_token, get_current_user
from app.config import settings
from app.db_session import get_db
from app.models import User
from app.schemas import UserOut
from app.services import spotify_client, user_service

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "session_token"


@router.get("/login")
def login() -> RedirectResponse:
    """Spotifyの認可画面へリダイレクトする。"""
    return RedirectResponse(spotify_client.get_authorize_url())


@router.get("/callback")
def callback(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """Spotifyからのコールバックを受け取り、ユーザーを作成/更新してセッションを発行する。"""
    token_info = spotify_client.exchange_code_for_token(code)
    user = user_service.upsert_user_from_token(db, token_info)
    db.commit()

    jwt_token = create_access_token(user.id)

    # 注意: Cookieはホスト名(ポートは無視)単位で共有されるため、
    # SPOTIFY_REDIRECT_URI と FRONTEND_URL のホスト名は必ず揃えること。
    # Spotifyはhttpの場合ループバックIPリテラル "127.0.0.1" のみ許可し
    # "localhost" は拒否するため、両方とも "127.0.0.1" に統一している。
    redirect = RedirectResponse(url=f"{settings.frontend_url}/battle?sync=1")
    redirect.set_cookie(
        key=COOKIE_NAME,
        value=jwt_token,
        httponly=True,
        secure=False,  # 本番でHTTPS運用する場合は True にする
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )
    return redirect


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(COOKIE_NAME)
    return {"detail": "ログアウトしました"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
