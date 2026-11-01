"""ユーザーのSpotifyトークン管理。

- トークンの暗号化/復号(DB保存用)
- OAuth認可後のUserレコード作成・更新(FastAPI・CLI共通)
- 有効なアクセストークンの取得(期限切れならリフレッシュ)

JWT・Cookieセッションまわり(API専用)は api/security.py にある。
"""

from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.services import spotify_client

_fernet = Fernet(settings.token_encryption_key.encode())


def _encrypt(raw_token: str) -> str:
    return _fernet.encrypt(raw_token.encode()).decode()


def _decrypt(encrypted_token: str) -> str:
    return _fernet.decrypt(encrypted_token.encode()).decode()


def upsert_user_from_token(db: Session, token_info: dict[str, Any]) -> User:
    """認可コード交換で得たトークン情報から、ユーザーをDBに作成/更新する。
    呼び出し側が db.commit() する前提(このAPI自体はcommitしない)。
    """
    profile = spotify_client.fetch_current_user_profile(token_info["access_token"])

    user = db.query(User).filter(User.spotify_user_id == profile["id"]).first()
    if user is None:
        user = User(spotify_user_id=profile["id"])

    user.display_name = profile.get("display_name")
    user.email = profile.get("email")
    user.access_token_encrypted = _encrypt(token_info["access_token"])
    user.refresh_token_encrypted = _encrypt(token_info["refresh_token"])
    user.token_expires_at = spotify_client.expires_at_from_expires_in(token_info["expires_in"])

    db.add(user)
    db.flush()
    db.refresh(user)

    return user


def get_valid_access_token(db: Session, user: User) -> str:
    """有効なアクセストークンを返す。期限切れならリフレッシュしてDBを更新する。"""
    now = datetime.now(timezone.utc)

    if user.token_expires_at > now:
        return _decrypt(user.access_token_encrypted)

    refresh_token = _decrypt(user.refresh_token_encrypted)
    token_info = spotify_client.refresh_access_token(refresh_token)

    user.access_token_encrypted = _encrypt(token_info["access_token"])
    user.token_expires_at = spotify_client.expires_at_from_expires_in(token_info["expires_in"])
    # Spotifyがrefresh_tokenを再発行する場合があるので更新
    if token_info.get("refresh_token"):
        user.refresh_token_encrypted = _encrypt(token_info["refresh_token"])

    db.add(user)
    db.commit()
    db.refresh(user)

    return _decrypt(user.access_token_encrypted)
