"""Tests for the AI analysis service."""

import json
from unittest.mock import patch

import pytest

from app.models.ad import Ad
from app.services.ai import AIService

# --- Response parsing ---


def test_parse_response_valid_json():
    content = '{"score": 7, "summary": "Gutes Angebot", "reasoning": "Günstig"}'
    result = AIService._parse_response(content)
    assert result["score"] == 7.0
    assert result["summary"] == "Gutes Angebot"
    assert result["reasoning"] == "Günstig"


def test_parse_response_with_markdown_fences():
    content = '```json\n{"score": 5, "summary": "Ok", "reasoning": "Fair"}\n```'
    result = AIService._parse_response(content)
    assert result["score"] == 5.0


def test_parse_response_score_out_of_range():
    content = '{"score": 15, "summary": "Test", "reasoning": "Test"}'
    with pytest.raises(ValueError, match="out of range"):
        AIService._parse_response(content)


def test_parse_response_empty():
    with pytest.raises(ValueError, match="Empty response"):
        AIService._parse_response(None)


def test_parse_response_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        AIService._parse_response("This is not JSON")


# --- Image type detection ---


def test_detect_jpeg():
    data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/jpeg"


def test_detect_png():
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/png"


def test_detect_webp():
    data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/webp"


def test_detect_gif():
    data = b"GIF89a" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/gif"


def test_detect_unknown():
    data = b"\x00\x00\x00\x00" + b"\x00" * 100
    assert AIService._detect_image_type(data) is None


# --- Price context ---


def test_build_price_context(session, sample_adsearch, sample_ads):
    """Test that price context includes comparison prices."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[0]  # price=55.0
    context = ai_service._build_price_context(ad)

    assert "Vergleichspreise" in context
    assert "80€" in context  # price of sample_ads[1]
    assert "15€" in context  # price of sample_ads[2]
    assert "Durchschnitt" in context
    assert "Median" in context


def test_build_price_context_no_other_ads(session, sample_adsearch):
    """Test price context when no other ads exist."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = Ad(
        external_id="9999",
        title="Lonely Ad",
        url="https://example.com",
        price=50.0,
        adsearch_id=sample_adsearch.id,
    )
    session.add(ad)
    session.commit()

    context = ai_service._build_price_context(ad)
    assert context == ""


# --- Ad text building ---


def test_build_ad_text(session, sample_adsearch, sample_ads):
    """Test building ad text for AI prompt."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[0]
    text = ai_service._build_ad_text(ad, sample_adsearch)

    assert "Rode PodMic" in text
    assert "55€" in text
    assert "Bewertung: TOP" in text


def test_build_ad_text_with_seller_rating_labels(session, sample_adsearch, sample_ads):
    """Test that seller rating is converted to label."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[1]  # seller_rating=1
    text = ai_service._build_ad_text(ad, sample_adsearch)
    assert "Bewertung: OK" in text

    ad = sample_ads[2]  # seller_rating=0
    text = ai_service._build_ad_text(ad, sample_adsearch)
    assert "Bewertung: Na ja" in text


# --- Analyze with mocked API ---


@patch("app.services.ai.settings")
def test_ai_service_raises_without_api_key(mock_settings, session):
    """Test that AIService raises ValueError without API key."""
    mock_settings.openrouter_api_key = ""
    with pytest.raises(ValueError, match="API key not configured"):
        AIService(session)
