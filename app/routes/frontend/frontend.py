"""Stellt das statisch exportierte Next.js-Frontend und SPA-Fallback-Routen bereit."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core import get_app_root

FRONTEND_OUT_DIR = get_app_root() / "web" / "out"
INDEX_HTML = FRONTEND_OUT_DIR / "index.html"


NO_CACHE_HEADERS = {"Cache-Control": "no-cache"}


def _serve_detail_page(section: str, id: int) -> FileResponse:
    """Liefert die vorgerenderte Detailseite für section/id oder die id=0-Hülle falls fehlend."""
    candidate = FRONTEND_OUT_DIR / section / str(id) / "index.html"
    if candidate.is_file():
        return FileResponse(candidate, headers=NO_CACHE_HEADERS)
    fallback = FRONTEND_OUT_DIR / section / "0" / "index.html"
    return FileResponse(
        fallback if fallback.is_file() else INDEX_HTML,
        headers=NO_CACHE_HEADERS,
    )


router = APIRouter(include_in_schema=False)


# SPA-Fallback: Direkte Aufrufe von /searches/5, /ads/21 erhalten die id=0-HTML-Hülle,
# damit der Client-Router hydrieren und Daten für die echte ID laden kann.
@router.api_route("/searches/{id:int}", methods=["GET", "HEAD"])
def serve_search_detail(id: int):
    """Liefert die SPA-Detail-Hülle für die gegebene Suchauftrags-ID."""
    return _serve_detail_page("searches", id)


@router.api_route("/ads/{id:int}", methods=["GET", "HEAD"])
def serve_ad_detail(id: int):
    """Liefert die SPA-Detail-Hülle für die gegebene Anzeigen-ID."""
    return _serve_detail_page("ads", id)


def mount_frontend(app):
    """Hängt das statische Next.js-Export unter / ein (nach dem Einbinden des Routers aufrufen)."""
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_OUT_DIR), html=True, check_dir=False),
        name="web",
    )
