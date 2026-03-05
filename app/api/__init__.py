from fastapi import APIRouter

from app.api.ads import router as ads_router
from app.api.adsearch import router as adsearch_router
from app.api.errorlogs import router as errorlogs_router
from app.api.scraperuns import router as scraperuns_router
from app.api.settings import router as settings_router

api_router = APIRouter(prefix="/api")
api_router.include_router(ads_router)
api_router.include_router(adsearch_router)
api_router.include_router(errorlogs_router)
api_router.include_router(scraperuns_router)
api_router.include_router(settings_router)
