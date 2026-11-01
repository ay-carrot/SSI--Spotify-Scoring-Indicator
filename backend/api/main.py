import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import auth, library, matches, rankings
from app import models  # noqa: F401  モデルをBaseに登録するため(create_allより前に必須)
from app.config import settings
from app.db_session import Base, engine
from app.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# 起動時にテーブルが無ければ作成する。
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Spotify Elo Rating API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未処理例外はサーバーログにスタックトレースを残しつつ、
    クライアントには簡潔なJSONを返す(生のトレースバックを見せない)。
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "サーバー内部でエラーが発生しました。"})


app.include_router(auth.router)
app.include_router(library.router)
app.include_router(matches.router)
app.include_router(rankings.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
