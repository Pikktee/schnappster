"""API-Route für die Anwendungsversion."""

from importlib.metadata import version

from fastapi import APIRouter

router = APIRouter(prefix="/version", tags=["Version"])


@router.get("/", response_model=dict)
def get_version() -> dict:
    """Gibt die Anwendungsversion aus den Paket-Metadaten (pyproject.toml) zurück."""
    return {"version": version("schnappster")}
