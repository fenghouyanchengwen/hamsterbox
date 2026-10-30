"""FastAPI 应用入口。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import health

APP_VERSION = "0.1.0"

app = FastAPI(title="HamsterBox API", version=APP_VERSION)
app.include_router(health.router, prefix="/api")


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}


_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
