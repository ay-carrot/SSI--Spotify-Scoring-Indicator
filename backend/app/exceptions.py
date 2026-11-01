"""アプリ共通の例外。

app/services/ は HTTP にもCLIにも依存しないため、エラーはこれらの例外で表現し、
呼び出し側(api/ は HTTPException へ、cli/ はメッセージ表示へ)が変換する。
"""


class AppError(Exception):
    """アプリ由来のエラーの基底クラス。"""


class NotFoundError(AppError):
    """対象のリソースが存在しない(HTTPなら404相当)。"""


class ValidationError(AppError):
    """入力値が不正、または処理の前提を満たさない(HTTPなら400相当)。"""
