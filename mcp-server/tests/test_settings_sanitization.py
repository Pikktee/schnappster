"""Tests für Settings-Sanitizing im MCP-Server."""

from schnappster_mcp.server import _sanitize_user_settings


def test_sanitize_user_settings_removes_deletion_pending() -> None:
    """`deletion_pending` wird aus den Tool-Antworten entfernt."""
    payload = {
        "user_id": "u_123",
        "display_name": "Henrik",
        "notify_min_score": 7,
        "deletion_pending": True,
    }

    sanitized = _sanitize_user_settings(payload)

    assert "deletion_pending" not in sanitized
    assert sanitized["display_name"] == "Henrik"
    assert sanitized["notify_min_score"] == 7


def test_sanitize_user_settings_keeps_unrelated_fields() -> None:
    """Unabhängige Felder bleiben unverändert erhalten."""
    payload = {"notify_telegram": True, "telegram_chat_id": "1234"}

    assert _sanitize_user_settings(payload) == payload
