"""Ensure monorepo .env discovery points at repo root and mcp-server."""

from schnappster_mcp.config import _dotenv_files, _mcp_project_dir


def test_dotenv_files_in_monorepo() -> None:
    """Im Monorepo: zuerst Root-``.env``, danach ``mcp-server/.env``."""
    mcp_dir = _mcp_project_dir()
    repo = mcp_dir.parent
    files = _dotenv_files()
    assert (repo / "app").is_dir()
    assert files[0] == repo / ".env"
    assert files[1] == mcp_dir / ".env"
