from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routes import documents, health, notes, query, settings as settings_routes, stores


app = FastAPI(title=settings.service_name)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/app")


@app.get("/app", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(static_dir / "index.html")


app.include_router(health.router)
app.include_router(stores.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(notes.router)
app.include_router(settings_routes.router)
