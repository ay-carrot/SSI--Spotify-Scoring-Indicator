from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Spotify
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://127.0.0.1:8000/auth/callback"
    spotify_scopes: str = "user-library-read user-read-email playlist-read-private playlist-read-collaborative"
    # CLI版ログイン用のコールバック先。Web版(上記)とはポートを分ける。
    # Spotify Developer Dashboardにこちらも追加登録しておくこと。
    spotify_cli_redirect_uri: str = "http://127.0.0.1:8765/callback"

    # DB
    database_url: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days
    token_encryption_key: str

    # Frontend (バックエンドと同じホスト名 "127.0.0.1" にすること。Cookie共有のため)
    frontend_url: str = "http://127.0.0.1:5173"

    # Elo
    elo_k_factor: float = 32.0
    elo_initial_rating: float = 1500.0


settings = Settings()
