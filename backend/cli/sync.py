"""プレイリスト一覧を表示し、選んだものを同期する。

使い方:
    python -m cli.sync
"""

from cli._session import db_session, prompt_select_many, require_login
from app.schemas import PlaylistOut
from app.services import library_service


def _label(i: int, p: PlaylistOut) -> str:
    return f"  [{i}] {p.name} ({p.track_count}曲)"


def main() -> None:
    with db_session() as db:
        user = require_login(db)

        print("プレイリストを取得中...")
        playlists = library_service.get_selectable_playlists(db, user)

        if not playlists:
            print("同期できるプレイリストがありませんでした。")
            return

        print("\n同期するプレイリストを選んでください:")
        selected = prompt_select_many(playlists, _label)

        if not selected:
            print("何も選択されませんでした。終了します。")
            return

        selected_ids = [p.id for p in selected]
        # 一覧取得時の名前を渡して、同期時のプレイリスト一覧の再取得を省く
        selected_names = {p.id: p.name for p in selected}
        print(f"\n{len(selected_ids)}件のプレイリストを同期します...")

        result = library_service.sync_playlists(db, user, selected_ids, selected_names)
        db.commit()

        print(f"同期完了: {result.fetched}曲取得 / 新規{result.created}曲 / 更新{result.updated}曲")
        if result.skipped_playlist_ids:
            print(
                f"取得できなかったプレイリスト: {len(result.skipped_playlist_ids)}件 "
                f"(Spotifyのおまかせ系プレイリストは取得できないことがあります)"
            )


if __name__ == "__main__":
    main()
