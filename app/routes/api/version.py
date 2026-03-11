"""Version API route."""

from importlib.metadata import version

from fastapi import APIRouter

router = APIRouter(prefix="/version", tags=["Version"])


@router.get("/", response_model=dict)
def get_version() -> dict:
    """Return application version from package metadata (pyproject.toml)."""
    return {"version": version("schnappster")}
