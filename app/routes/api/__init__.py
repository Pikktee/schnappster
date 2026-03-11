"""API route modules; api_router includes all API routers under /api."""

from fastapi import APIRouter

from app.routes.api.ads import router as ads_router
from app.routes.api.adsearch import router as adsearch_router
from app.routes.api.errorlogs import router as errorlogs_router
from app.routes.api.scraperuns import router as scraperuns_router
from app.routes.api.settings import router as settings_router
from app.routes.api.version import router as version_router

api_router = APIRouter(prefix="/api")
api_router.include_router(ads_router)
api_router.include_router(adsearch_router)
api_router.include_router(errorlogs_router)
api_router.include_router(scraperuns_router)
api_router.include_router(settings_router)
api_router.include_router(version_router)
