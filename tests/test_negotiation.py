"""Tests für den Verhandlungs-Assistenten (Kontext, Prompt, Endpunkt)."""

from unittest.mock import patch

from app.models.ad import Ad
from app.prompts import render_negotiation_prompt
from app.services.ai import AIService


def _priced_ad() -> Ad:
    return Ad(
        owner_id="x",
        external_id="1",
        title="Rode PodMic",
        url="https://www.kleinanzeigen.de/s-anzeige/rode-podmic/1",
        price=60.0,
        condition="Sehr gut",
        estimated_market_price=90.0,
        price_delta_percent=33.3,
        comparison_summary="Median aus 5 Vergleichen: 90 EUR",
    )


# --- Kontextaufbau (statisch, ohne API-Key/DB) ---


def test_build_negotiation_context_priced():
    """Bepreiste Anzeige: is_priced True, Preis-/Marktwert-Felder gesetzt."""
    ctx = AIService._build_negotiation_context(_priced_ad())
    assert ctx["is_priced"] is True
    assert ctx["price_display"] == "60€"
    assert ctx["market_price"] == 90.0
    assert ctx["condition"] == "Sehr gut"


def test_build_negotiation_context_without_price():
    """Ohne Preis (VB/zu verschenken): is_priced False, kein fester Preis."""
    ad = Ad(owner_id="x", external_id="2", title="Sofa", url="https://x/2", price=None)
    ctx = AIService._build_negotiation_context(ad)
    assert ctx["is_priced"] is False
    assert "kein fester Preis" in ctx["price_display"]


def test_build_negotiation_context_truncates_long_description():
    """Sehr lange Beschreibungen werden für den Prompt gekürzt."""
    ad = Ad(
        owner_id="x",
        external_id="3",
        title="Ding",
        url="https://x/3",
        price=10.0,
        description="A" * 1000,
    )
    ctx = AIService._build_negotiation_context(ad)
    assert len(ctx["description"]) <= 401
    assert ctx["description"].endswith("…")


# --- Prompt-Rendering ---


def test_render_negotiation_prompt_priced():
    """Prompt enthält Titel, Preis und die JSON-Vorgabe; fordert ein Gegenangebot."""
    prompt = render_negotiation_prompt(AIService._build_negotiation_context(_priced_ad()))
    assert "Rode PodMic" in prompt
    assert "60€" in prompt
    assert "JSON" in prompt
    assert "suggested_offer" in prompt


def test_render_negotiation_prompt_unpriced_asks_no_offer():
    """Ohne Preis weist der Prompt an, KEIN konkretes Angebot zu machen."""
    ad = Ad(owner_id="x", external_id="4", title="Sofa", url="https://x/4", price=None)
    prompt = render_negotiation_prompt(AIService._build_negotiation_context(ad))
    assert "KEIN konkretes Preisangebot" in prompt


# --- Endpunkt (AIService gemockt, kein echter API-Call) ---


@patch("app.routes.api.ads.AIService")
def test_negotiation_endpoint_success(mock_ai_cls, client, sample_ads):
    """POST liefert die generierte Nachricht + Gegenangebot."""
    mock_ai_cls.return_value.generate_negotiation_message.return_value = {
        "message": "Hallo, ist das PodMic noch zu haben? Ich würde 45€ bieten.",
        "suggested_offer": 45.0,
        "reasoning": "45€ liegt leicht unter dem üblichen Marktpreis.",
    }
    ad = sample_ads[0]

    response = client.post(f"/ads/{ad.id}/negotiation-message")

    assert response.status_code == 200
    body = response.json()
    assert body["message"].startswith("Hallo")
    assert body["suggested_offer"] == 45.0
    assert body["reasoning"]
    mock_ai_cls.return_value.generate_negotiation_message.assert_called_once()


def test_negotiation_endpoint_404_for_unknown_ad(client):
    """POST auf unbekannte Anzeige → 404."""
    response = client.post("/ads/999999/negotiation-message")
    assert response.status_code == 404


@patch("app.routes.api.ads.AIService", side_effect=ValueError("API key not configured"))
def test_negotiation_endpoint_503_without_api_key(_mock_ai_cls, client, sample_ads):
    """Ohne konfigurierten API-Key → 503 mit klarer Meldung."""
    response = client.post(f"/ads/{sample_ads[0].id}/negotiation-message")
    assert response.status_code == 503
