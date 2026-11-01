from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db_session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    spotify_user_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)

    access_token_encrypted: Mapped[str] = mapped_column(String)
    refresh_token_encrypted: Mapped[str] = mapped_column(String)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    spotify_track_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    artist_name: Mapped[str] = mapped_column(String)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)


class TrackPlaylistMembership(Base):
    """「このユーザーのこの曲は、どのプレイリスト(=対戦プール)由来か」を表す。

    対戦は常に1プレイリスト単位で行う設計のため、レーティングもここに
    (user_id, track_id, playlist_id)単位で持つ。同じ曲でも所属プレイリストが
    複数あれば、プールごとに独立したレートを持つ。
    """

    __tablename__ = "track_playlist_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "track_id", "playlist_id", name="uq_user_track_playlist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)

    # Spotifyのプレイリストid、または疑似id "liked_songs"
    playlist_id: Mapped[str] = mapped_column(String, index=True)
    # 表示用に名前をここにも複製して持つ(プレイリスト自体のマスタは持たない設計のため)
    playlist_name: Mapped[str] = mapped_column(String)

    # このプール内でのEloレーティング・対戦回数
    rating: Mapped[float] = mapped_column(Float, default=1500.0)
    match_count: Mapped[int] = mapped_column(Integer, default=0)

    track: Mapped["Track"] = relationship()
