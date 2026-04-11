"""Tests für das Rendern der Prompt-Vorlagen."""

from app.prompts import render_system_prompt, render_user_prompt


def test_system_prompt_contains_rating_scale():
    """Der gerenderte System-Prompt enthält die feste Bewertungsskala (0–10 mit Labels)."""
    assert "Bewertungsskala (0-10)" in render_system_prompt()
    assert "0-2:" in render_system_prompt() and "Überteuert" in render_system_prompt()
    assert "5:" in render_system_prompt() and "Normaler Gebrauchtpreis" in render_system_prompt()
    assert "8-9:" in render_system_prompt() and "Echtes Schnäppchen" in render_system_prompt()
    assert "10:" in render_system_prompt() and "Unglaublich günstig" in render_system_prompt()


def test_system_prompt_contains_json_instruction():
    """Der gerenderte System-Prompt verlangt das JSON-Ausgabeformat."""
    assert "Antworte AUSSCHLIESSLICH im folgenden JSON-Format" in render_system_prompt()
    assert '"score"' in render_system_prompt()
    assert '"summary"' in render_system_prompt()
    assert '"reasoning"' in render_system_prompt()


def test_system_prompt_contains_injection_guard():
    """System-Prompt: Nutzerkontext darf das Antwortformat nicht überschreiben."""
    assert "Zusätzliche Bewertungshinweise" in render_system_prompt()
    assert "verbindlich" in render_system_prompt()
    assert "User-Nachricht" in render_system_prompt()


def test_system_prompt_starts_with_role():
    """Der gerenderte System-Prompt definiert die Analysten-Rolle."""
    assert "Schnäppchen-Analyst" in render_system_prompt()
    assert "Kleinanzeigen" in render_system_prompt()


def test_render_user_prompt_minimal():
    """Nutzerinhalt mit nur Titel und price_display zeigt die Labels."""
    out = render_user_prompt({"title": "Testartikel", "price_display": "50€"})
    assert "Titel: Testartikel" in out
    assert "Preis: 50€" in out


def test_render_user_prompt_with_comparison():
    """Nutzerinhalt mit comparison zeigt den Vergleichsangebote-Block mit Titeln und Preisen."""
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
    """Nutzerinhalt mit user_instructions endet mit markiertem Block."""
    out = render_user_prompt({
        "title": "X",
        "price_display": "1€",
        "user_instructions": "Bevorzuge unbenutzte Artikel",
    })
    assert "[Zusätzliche Bewertungshinweise]" in out
    assert "Bevorzuge unbenutzte Artikel" in out
    assert "[Ende der Bewertungshinweise]" in out


def test_render_user_prompt_seller_rating():
    """Nutzerinhalt mit seller_name und seller_rating 2 zeigt Verkäufer-Block mit TOP."""
    out = render_user_prompt({
        "title": "X",
        "price_display": "5€",
        "seller_name": "Testverkäufer",
        "seller_rating": 2,
    })
    assert "Verkäufer" in out
    assert "Testverkäufer" in out
    assert "TOP" in out
