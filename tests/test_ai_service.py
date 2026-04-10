"""Tests für den KI-Analyse-Service."""

import json
from unittest.mock import patch

import pytest

from app.models.ad import Ad
from app.prompts import render_user_prompt
from app.services.ai import AIService

# --- Response parsen ---


def test_parse_response_valid_json():
    """Gültige JSON-Antwort wird zu score, summary, reasoning geparst."""
    content = '{"score": 7, "summary": "Gutes Angebot", "reasoning": "Günstig"}'
    result = AIService._parse_response(content)
    assert result["score"] == 7.0
    assert result["summary"] == "Gutes Angebot"
    assert result["reasoning"] == "Günstig"


def test_parse_response_with_markdown_fences():
    """JSON innerhalb von Markdown-Code-Fences wird extrahiert und geparst."""
    content = '```json\n{"score": 5, "summary": "Ok", "reasoning": "Fair"}\n```'
    result = AIService._parse_response(content)
    assert result["score"] == 5.0


def test_parse_response_score_out_of_range():
    """Score außerhalb 0–10 löst ValueError aus."""
    content = '{"score": 15, "summary": "Test", "reasoning": "Test"}'
    with pytest.raises(ValueError, match="außerhalb"):
        AIService._parse_response(content)


def test_parse_response_empty():
    """None oder leerer Inhalt löst ValueError aus."""
    with pytest.raises(ValueError, match="Leere Antwort"):
        AIService._parse_response(None)


def test_parse_response_invalid_json():
    """Nicht-JSON-Inhalt löst JSONDecodeError aus."""
    with pytest.raises(json.JSONDecodeError):
        AIService._parse_response("This is not JSON")


# --- Bildtyp-Erkennung ---


def test_detect_jpeg():
    """JPEG-Magic-Bytes werden als image/jpeg erkannt."""
    data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/jpeg"


def test_detect_png():
    """PNG-Magic-Bytes werden als image/png erkannt."""
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/png"


def test_detect_webp():
    """WebP-Magic-Bytes werden als image/webp erkannt."""
    data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/webp"


def test_detect_gif():
    """GIF-Magic-Bytes werden als image/gif erkannt."""
    data = b"GIF89a" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/gif"


def test_detect_unknown():
    """Unbekannte Magic-Bytes liefern None."""
    data = b"\x00\x00\x00\x00" + b"\x00" * 100
    assert AIService._detect_image_type(data) is None


# --- Preiskontext ---


def test_build_price_context(session, sample_adsearch, sample_ads):
    """Preiskontext liefert Dict mit Einträgen (Titel+Preis), Durchschnitt und Median aus demselben Suchauftrag."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[0]  # price=55.0
    context = ai_service._build_price_context(ad)

    assert context is not None
    assert "entries" in context
    assert "prices" in context
    assert "price_list" in context
    assert "average" in context
    assert "median" in context
    assert context["count"] == 2  # sample_ads[1] and [2]
    assert "80" in context["price_list"]
    assert "15" in context["price_list"]
    titles = [e["title"] for e in context["entries"]]
    assert "Rode PodMic USB" in titles
    assert "Rode PodMic defekt" in titles


def test_build_price_context_no_other_ads(session, sample_adsearch):
    """Preiskontext ist None, wenn keine anderen Anzeigen im selben Suchauftrag sind."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = Ad(
        owner_id="00000000-0000-0000-0000-000000000001",
        external_id="9999",
        title="Lonely Ad",
        url="https://example.com",
        price=50.0,
        adsearch_id=sample_adsearch.id,
    )
    session.add(ad)
    session.commit()

    context = ai_service._build_price_context(ad)
    assert context is None


# --- Nutzerkontext und gerenderter Text ---


def test_build_user_context_and_render(session, sample_adsearch, sample_ads):
    """Nutzerkontext + Render erzeugt Text mit Titel, Preis, Verkäufer-Rating, Vergleich."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[0]
    context = ai_service._build_user_context(ad, sample_adsearch)
    text = render_user_prompt(context)

    assert "Rode PodMic" in text
    assert "55€" in text
    assert "Bewertung: TOP" in text


def test_build_user_context_seller_rating_labels(session, sample_adsearch, sample_ads):
    """Verkäufer-Rating 1 und 0 erscheinen als OK und Na ja im gerenderten Inhalt."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[1]  # seller_rating=1
    context = ai_service._build_user_context(ad, sample_adsearch)
    text = render_user_prompt(context)
    assert "Bewertung: OK" in text

    ad = sample_ads[2]  # seller_rating=0
    context = ai_service._build_user_context(ad, sample_adsearch)
    text = render_user_prompt(context)
    assert "Bewertung: Na ja" in text


def test_build_user_context_without_prompt_addition(session, sample_adsearch, sample_ads):
    """Gerenderter Nutzerinhalt hat keinen Anweisungsblock, wenn prompt_addition nicht gesetzt ist."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session
    ad = sample_ads[0]
    context = ai_service._build_user_context(ad, sample_adsearch)
    assert context.get("user_instructions") is None
    text = render_user_prompt(context)
    assert "[Zusätzliche Bewertungshinweise]" not in text


# --- Analyse mit gemockter API ---


@patch("app.services.ai.app_config")
def test_ai_service_raises_without_api_key(mock_app_config, session):
    """AIService löst ValueError aus, wenn OPENAI_API_KEY nicht gesetzt ist."""
    mock_app_config.openai_api_key = ""
    with pytest.raises(ValueError, match="API key not configured"):
        AIService(session)
