from fastapi import APIRouter

from app.routes.ads import router as ads_router
from app.routes.adsearch import router as adsearch_router
from app.routes.errorlogs import router as errorlogs_router
from app.routes.scraperuns import router as scraperuns_router
from app.routes.settings import router as settings_router

api_router = APIRouter(prefix="/api")
api_router.include_router(ads_router)
api_router.include_router(adsearch_router)
api_router.include_router(errorlogs_router)
api_router.include_router(scraperuns_router)
api_router.include_router(settings_router)
