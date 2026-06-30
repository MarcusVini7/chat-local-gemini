from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.routes import documents, health, query, stores


app = FastAPI(title=settings.service_name)


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(health.router)
app.include_router(stores.router)
app.include_router(documents.router)
app.include_router(query.router)
