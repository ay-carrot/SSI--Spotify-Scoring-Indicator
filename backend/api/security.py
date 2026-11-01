"""APIのログインセッション(JWT + Cookie)と、ログイン中ユーザーの解決。

FastAPIの Cookie 依存を使うため、api/ 側に置く(cli/ はローカルファイルで
セッションを管理しており、こちらには依存しない)。
"""

from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db_session import get_db
from app.models import User


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="認証情報が無効です")


def get_current_user_id(session_token: str | None = Cookie(default=None)) -> int:
    if session_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ログインが必要です")
    return decode_access_token(session_token)


def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    """ログイン中のUserを返す。Cookieは有効でもDB上にユーザーがいない場合
    (DBを作り直した後の古いCookieなど)は、未ログイン扱いの401にする。
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ユーザーが見つかりません")
    return user
