"""同期済みのプール一覧から選んで、そのプールのランキングを表示する。

使い方:
    python -m cli.rankings
"""

from cli._session import db_session, pool_label, prompt_select_one, require_login
from app.services import battle_service


def main() -> None:
    with db_session() as db:
        user = require_login(db)

        pools = battle_service.get_pools(db, user.id)
        if not pools:
            print("同期済みのプールがありません。先に `python -m cli.sync` を実行してください。")
            return

        print("表示するプールを選んでください:")
        selected = prompt_select_one(pools, pool_label)
        if selected is None:
            print("キャンセルしました。")
            return

        tracks = battle_service.get_pool_rankings(db, user.id, selected.playlist_id, limit=100)

        print(f"\n=== 「{selected.playlist_name}」ランキング ===")
        for i, t in enumerate(tracks, start=1):
            print(f"{i:>3}. {round(t.rating):>5}  {t.name} - {t.artist_name}  ({t.match_count}戦)")


if __name__ == "__main__":
    main()
