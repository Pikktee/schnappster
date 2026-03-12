"""Tests for the AI analysis service."""

import json
from unittest.mock import patch

import pytest

from app.models.ad import Ad
from app.prompts import render_user_content
from app.services.ai import AIService

# --- Response parsing ---


def test_parse_response_valid_json():
    """Valid JSON response is parsed to score, summary, reasoning."""
    content = '{"score": 7, "summary": "Gutes Angebot", "reasoning": "Günstig"}'
    result = AIService._parse_response(content)
    assert result["score"] == 7.0
    assert result["summary"] == "Gutes Angebot"
    assert result["reasoning"] == "Günstig"


def test_parse_response_with_markdown_fences():
    """JSON inside markdown code fences is extracted and parsed."""
    content = '```json\n{"score": 5, "summary": "Ok", "reasoning": "Fair"}\n```'
    result = AIService._parse_response(content)
    assert result["score"] == 5.0


def test_parse_response_score_out_of_range():
    """Score outside 0-10 raises ValueError."""
    content = '{"score": 15, "summary": "Test", "reasoning": "Test"}'
    with pytest.raises(ValueError, match="out of range"):
        AIService._parse_response(content)


def test_parse_response_empty():
    """None or empty content raises ValueError."""
    with pytest.raises(ValueError, match="Empty response"):
        AIService._parse_response(None)


def test_parse_response_invalid_json():
    """Non-JSON content raises JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        AIService._parse_response("This is not JSON")


# --- Image type detection ---


def test_detect_jpeg():
    """JPEG magic bytes are detected as image/jpeg."""
    data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/jpeg"


def test_detect_png():
    """PNG magic bytes are detected as image/png."""
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/png"


def test_detect_webp():
    """WebP magic bytes are detected as image/webp."""
    data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/webp"


def test_detect_gif():
    """GIF magic bytes are detected as image/gif."""
    data = b"GIF89a" + b"\x00" * 100
    assert AIService._detect_image_type(data) == "image/gif"


def test_detect_unknown():
    """Unknown magic bytes return None."""
    data = b"\x00\x00\x00\x00" + b"\x00" * 100
    assert AIService._detect_image_type(data) is None


# --- Price context ---


def test_build_price_context(session, sample_adsearch, sample_ads):
    """Price context returns dict with comparison prices, average and median from same AdSearch."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[0]  # price=55.0
    context = ai_service._build_price_context(ad)

    assert context is not None
    assert "prices" in context
    assert "price_list" in context
    assert "average" in context
    assert "median" in context
    assert context["count"] == 2  # sample_ads[1] and [2]
    assert "80" in context["price_list"]
    assert "15" in context["price_list"]


def test_build_price_context_no_other_ads(session, sample_adsearch):
    """Price context is None when no other ads in same AdSearch."""
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
    assert context is None


# --- User context and rendered text ---


def test_build_user_context_and_render(session, sample_adsearch, sample_ads):
    """User context + render produces text with title, price, seller rating, comparison."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[0]
    context = ai_service._build_user_context(ad, sample_adsearch)
    text = render_user_content(context)

    assert "Rode PodMic" in text
    assert "55€" in text
    assert "Bewertung: TOP" in text


def test_build_user_context_seller_rating_labels(session, sample_adsearch, sample_ads):
    """Seller rating 1 and 0 appear as OK and Na ja in rendered content."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    ad = sample_ads[1]  # seller_rating=1
    context = ai_service._build_user_context(ad, sample_adsearch)
    text = render_user_content(context)
    assert "Bewertung: OK" in text

    ad = sample_ads[2]  # seller_rating=0
    context = ai_service._build_user_context(ad, sample_adsearch)
    text = render_user_content(context)
    assert "Bewertung: Na ja" in text


def test_build_user_context_without_prompt_addition(session, sample_adsearch, sample_ads):
    """Rendered user content has no instructions block when prompt_addition is not set."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session
    ad = sample_ads[0]
    context = ai_service._build_user_context(ad, sample_adsearch)
    assert context.get("user_instructions") is None
    text = render_user_content(context)
    assert "[Zusätzliche Bewertungshinweise]" not in text


# --- Analyze with mocked API ---


@patch("app.services.ai.app_config")
def test_ai_service_raises_without_api_key(mock_app_config, session):
    """AIService raises ValueError when OPENAI_API_KEY is not set."""
    mock_app_config.openai_api_key = ""
    with pytest.raises(ValueError, match="API key not configured"):
        AIService(session)
