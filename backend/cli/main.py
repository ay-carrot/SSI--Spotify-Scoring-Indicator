"""CLIのエントリーポイント。

状態(State)を持ったループとして構成し、メインメニューから
ログイン/同期/対戦/ランキング/ログアウトの各状態へ遷移する。
メインメニュー以外の状態は、対応する処理を1回実行したあとメインメニューに戻る。

使い方:
    python -m cli.main
"""

from enum import Enum, auto

from cli import _session, battle, login, rankings, sync
from app.models import User


class State(Enum):
    MAIN_MENU = auto()
    LOGIN = auto()
    SYNC = auto()
    BATTLE = auto()
    RANKINGS = auto()
    LOGOUT = auto()
    EXIT = auto()


def _logout() -> None:
    """ローカルのログインセッションを削除する(DB上のSpotifyトークンは残す)。"""
    _session.clear_session()
    print("ログアウトしました(ローカルのセッション情報を削除しました)。")


# メインメニュー以外の状態 → その状態で実行する処理(実行後はメインメニューに戻る)
_COMMANDS = {
    State.LOGIN: login.main,
    State.SYNC: sync.main,
    State.BATTLE: battle.main,
    State.RANKINGS: rankings.main,
    State.LOGOUT: _logout,
}


def _handle_main_menu() -> State:
    user_id = _session.load_session_user_id()

    label = "未ログイン"
    if user_id is not None:
        with _session.db_session() as db:
            user = db.get(User, user_id)
            if user is not None:
                label = f"ログイン中: {user.display_name or user.spotify_user_id}"

    if user_id is None:
        options = [("1", "ログイン (Spotify)", State.LOGIN)]
    else:
        options = [
            ("1", "プレイリスト同期", State.SYNC),
            ("2", "対戦", State.BATTLE),
            ("3", "ランキング", State.RANKINGS),
            ("4", "ログアウト", State.LOGOUT),
        ]
    options.append(("0", "終了", State.EXIT))

    print("\n" + "=" * 32)
    print("  SSI CLI")
    print("=" * 32)
    print(f"状態: {label}\n")
    for key, text, _ in options:
        print(f"[{key}] {text}")

    choice = input("選択: ").strip()
    return {key: state for key, _, state in options}.get(choice, State.MAIN_MENU)


def main() -> None:
    state = State.MAIN_MENU
    try:
        while state != State.EXIT:
            try:
                if state == State.MAIN_MENU:
                    state = _handle_main_menu()
                else:
                    _COMMANDS[state]()
                    state = State.MAIN_MENU
            except SystemExit:
                # 各サブコマンドの require_login() 等が異常系で sys.exit する場合があるが、
                # メインメニューのループ自体は終了させず、メニューに戻す。
                state = State.MAIN_MENU
    except KeyboardInterrupt:
        print()  # Ctrl+Cの改行を整える

    print("終了します。")


if __name__ == "__main__":
    main()
