from importlib.metadata import version

from fastapi import APIRouter

router = APIRouter(prefix="/version", tags=["Version"])


@router.get("/", response_model=dict)
def get_version() -> dict:
    """
    Return the application version (from pyproject.toml).
    """
    return {"version": version("schnappster")}
