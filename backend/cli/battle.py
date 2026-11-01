"""起動時に同期済みのプール(プレイリスト)一覧をDBから表示し、番号で選んで
対戦を開始する。

使い方:
    python -m cli.battle
"""

from cli._session import db_session, pool_label, prompt_select_one, require_login
from app.exceptions import AppError
from app.schemas import MatchResult, RankedTrackOut
from app.services import battle_service


def _track_label(mark: str, t: RankedTrackOut) -> str:
    return f"  [{mark}] {t.name} - {t.artist_name}  (elo {round(t.rating)}, {t.match_count}戦)"


def _battle_loop(db, user_id: int, playlist_id: str, playlist_name: str) -> None:
    print(f"\n=== 「{playlist_name}」で対戦開始 ===")
    print("1 または 2 で好きな方を選択、d=引き分け、q=終了\n")

    match_count = 0
    while True:
        try:
            pair = battle_service.get_battle_pair(db, user_id, playlist_id)
        except AppError as e:
            print(str(e))
            break

        track_a, track_b = pair.track_a, pair.track_b
        print(_track_label("1", track_a))
        print(_track_label("2", track_b))

        choice = input("選択 (1/2/d/q): ").strip().lower()
        if choice == "q":
            break
        if choice not in ("1", "2", "d"):
            print("1, 2, d, q のいずれかを入力してください。\n")
            continue

        result: MatchResult = "a_win" if choice == "1" else "b_win" if choice == "2" else "draw"

        try:
            match_result = battle_service.submit_match(
                db, user_id, playlist_id, track_a.id, track_b.id, result
            )
        except AppError as e:
            print(f"エラー: {e}\n")
            continue

        db.commit()
        match_count += 1

        new_a, new_b = match_result.track_a, match_result.track_b
        print(
            f"  -> {new_a.name}: {round(track_a.rating)} → {round(new_a.rating)}"
            f" / {new_b.name}: {round(track_b.rating)} → {round(new_b.rating)}\n"
        )

    print(f"お疲れさまでした。今回の対戦数: {match_count}戦")


def main() -> None:
    with db_session() as db:
        user = require_login(db)

        pools = battle_service.get_pools(db, user.id)
        if not pools:
            print("同期済みのプールがありません。先に `python -m cli.sync` を実行してください。")
            return

        print("対戦するプールを選んでください:")
        selected = prompt_select_one(pools, pool_label)
        if selected is None:
            print("キャンセルしました。")
            return

        _battle_loop(db, user.id, selected.playlist_id, selected.playlist_name)


if __name__ == "__main__":
    main()
