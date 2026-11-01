"""CLI共通のヘルパー。

- ログイン中ユーザーをローカルファイルに覚えておく(Web版のCookieセッションに相当)
- DBセッションの取得
- 番号選択の共通UI部品
"""

import json
import sys
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from sqlalchemy.orm import Session

from app.db_session import SessionLocal
from app.models import User
from app.schemas import RankingFilterOut

SESSION_DIR = Path.home() / ".spotify_elo_cli"
SESSION_FILE = SESSION_DIR / "session.json"

T = TypeVar("T")


def save_session(user_id: int) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps({"user_id": user_id}), encoding="utf-8")


def load_session_user_id() -> int | None:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        return data.get("user_id")
    except (json.JSONDecodeError, OSError):
        return None


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_login(db: Session) -> User:
    """ログイン中ユーザーを返す。未ログインならエラーメッセージを出して終了する。"""
    user_id = load_session_user_id()
    if user_id is None:
        print("ログインしていません。先に `python -m cli.login` を実行してください。")
        sys.exit(1)

    user = db.get(User, user_id)
    if user is None:
        print("ログイン情報が壊れているようです。`python -m cli.login` からやり直してください。")
        clear_session()
        sys.exit(1)

    return user


def pool_label(i: int, p: RankingFilterOut) -> str:
    """プール(同期済みプレイリスト)一覧用の表示ラベル。prompt_select_one に渡す。"""
    return f"  [{i}] {p.playlist_name} ({p.track_count}曲)"


def prompt_select_one(items: Iterable[T], label: Callable[[int, T], str]) -> T | None:
    """番号付きで一覧表示し、1つ選ばせる。キャンセル(空入力/q)なら None を返す。"""
    items = list(items)
    if not items:
        return None

    for i, item in enumerate(items, start=1):
        print(label(i, item))

    raw = input("番号を選択してください (q=キャンセル): ").strip()
    if raw.lower() in ("", "q"):
        return None

    try:
        idx = int(raw)
    except ValueError:
        print("数字を入力してください。")
        return prompt_select_one(items, label)

    if not (1 <= idx <= len(items)):
        print(f"1〜{len(items)}の番号を入力してください。")
        return prompt_select_one(items, label)

    return items[idx - 1]


def prompt_select_many(items: Iterable[T], label: Callable[[int, T], str]) -> list[T]:
    """番号付きで一覧表示し、カンマ区切りで複数選ばせる(例: 1,3,4)。"""
    items = list(items)
    if not items:
        return []

    for i, item in enumerate(items, start=1):
        print(label(i, item))

    raw = input("番号をカンマ区切りで選択してください (例: 1,3): ").strip()
    if not raw:
        return []

    selected: list[T] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part)
        except ValueError:
            print(f"'{part}' は数字ではないため無視します。")
            continue
        if 1 <= idx <= len(items):
            selected.append(items[idx - 1])
        else:
            print(f"'{part}' は範囲外のため無視します。")

    return selected
