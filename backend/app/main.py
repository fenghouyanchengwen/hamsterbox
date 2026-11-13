"""FastAPI 应用入口。"""

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from app.api import entries, entry_search, entry_tags, health, resources, tags
from app.application.errors import CodedApplicationError
from app.db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

APP_VERSION = "0.1.0"

app = FastAPI(
    title="HamsterBox API",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.include_router(health.router, prefix="/api")
app.include_router(entries.router, prefix="/api")
app.include_router(entry_search.router, prefix="/api")
app.include_router(resources.entry_resource_router, prefix="/api")
app.include_router(resources.resource_router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(tags.tag_router, prefix="/api")
app.include_router(entry_tags.router, prefix="/api")


@app.exception_handler(CodedApplicationError)
async def coded_application_error_handler(
    request: Request,
    exc: CodedApplicationError,
) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": str(exc),
            "details": {},
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    del request
    locations = {
        str(part)
        for error in exc.errors()
        for part in error.get("loc", ())
    }
    if "color" in locations:
        code = "TAG_CATEGORY_COLOR_INVALID"
    elif "rating" in locations:
        code = "RATING_OUT_OF_RANGE"
    else:
        code = "VALIDATION_ERROR"
    return JSONResponse(
        status_code=422,
        content={
            "code": code,
            "message": "请求字段校验失败",
            "details": {"errors": exc.errors()},
        },
    )

@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}


if getattr(sys, "frozen", False):
    _project_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    _project_root = Path(__file__).resolve().parents[2]

_dist = _project_root / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
