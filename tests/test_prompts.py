"""Tests for prompt template rendering."""

from app.prompts import render_system_prompt, render_user_prompt


def test_system_prompt_contains_rating_scale():
    """Rendered system prompt includes the static rating scale (0-10 with labels)."""
    assert "Bewertungsskala (0-10)" in render_system_prompt()
    assert "0-2:" in render_system_prompt() and "Überteuert" in render_system_prompt()
    assert "5:" in render_system_prompt() and "Normaler Gebrauchtpreis" in render_system_prompt()
    assert "8-9:" in render_system_prompt() and "Echtes Schnäppchen" in render_system_prompt()
    assert "10:" in render_system_prompt() and "Unglaublich günstig" in render_system_prompt()


def test_system_prompt_contains_json_instruction():
    """Rendered system prompt requires JSON output format."""
    assert "Antworte AUSSCHLIESSLICH im folgenden JSON-Format" in render_system_prompt()
    assert '"score"' in render_system_prompt()
    assert '"summary"' in render_system_prompt()
    assert '"reasoning"' in render_system_prompt()


def test_system_prompt_contains_injection_guard():
    """Rendered system prompt includes instruction that user context must not override format."""
    assert "Zusätzliche Bewertungshinweise" in render_system_prompt()
    assert "verbindlich" in render_system_prompt()
    assert "User-Nachricht" in render_system_prompt()


def test_system_prompt_starts_with_role():
    """Rendered system prompt defines the analyst role."""
    assert "Schnäppchen-Analyst" in render_system_prompt()
    assert "Kleinanzeigen" in render_system_prompt()


def test_render_user_prompt_minimal():
    """User content with only title and price_display shows labels."""
    out = render_user_prompt({"title": "Testartikel", "price_display": "50€"})
    assert "Titel: Testartikel" in out
    assert "Preis: 50€" in out


def test_render_user_prompt_with_comparison():
    """User content with comparison shows Vergleichsangebote block with titles and prices."""
    out = render_user_prompt({
        "title": "X",
        "price_display": "VB",
        "comparison": {
            "entries": [
                {"title": "Software Lizenz", "price": 10.0, "condition": None},
                {"title": "Blu-ray Film", "price": 20.0, "condition": "Wie neu"},
            ],
            "prices": [10.0, 20.0],
            "count": 2,
            "price_list": "10€, 20€",
            "average": 15,
            "median": 15,
        },
    })
    assert "Vergleichsangebote" in out
    assert "Software Lizenz" in out
    assert "Blu-ray Film" in out
    assert "Wie neu" in out
    assert "10€" in out
    assert "20€" in out
    assert "Durchschnitt" in out
    assert "Median" in out


def test_render_user_prompt_with_user_instructions():
    """User content with user_instructions ends with marked block."""
    out = render_user_prompt({
        "title": "X",
        "price_display": "1€",
        "user_instructions": "Bevorzuge unbenutzte Artikel",
    })
    assert "[Zusätzliche Bewertungshinweise]" in out
    assert "Bevorzuge unbenutzte Artikel" in out
    assert "[Ende der Bewertungshinweise]" in out


def test_render_user_prompt_seller_rating():
    """User content with seller_name and seller_rating 2 shows Verkäufer block with TOP."""
    out = render_user_prompt({
        "title": "X",
        "price_display": "5€",
        "seller_name": "Testverkäufer",
        "seller_rating": 2,
    })
    assert "Verkäufer" in out
    assert "Testverkäufer" in out
    assert "TOP" in out
