from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.ads import router as ads_router
from app.api.routes.adsearch import router as adsearch_router
from app.api.routes.settings import router as settings_router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Schnappster",
    version="0.1.0",
    description="Kleinanzeigen.de Schnäppchen-Finder",
    lifespan=lifespan,
)

app.include_router(adsearch_router, prefix="/api")
app.include_router(ads_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
