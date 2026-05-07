"""Tests für den KI-Analyse-Service."""

import json
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.ad import Ad
from app.prompts import render_user_prompt
from app.services.ai import AIService
from app.services.deal_analysis import (
    ComparisonCandidate,
    ComparisonJudgement,
    DealAnalysisResult,
    FinalDealResult,
    MarketEstimate,
    ProductExtraction,
)

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
    """Preiskontext: Einträge (Titel+Preis), Durchschnitt, Median im selben Suchauftrag."""
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


def test_build_comparison_candidates_respects_config_limit(session, sample_adsearch, sample_ads):
    """Evidence pipeline uses a bounded same-search candidate list."""
    ai_service = AIService.__new__(AIService)
    ai_service.session = session

    with patch("app.services.ai.app_config.ai_max_comparison_candidates", 1):
        candidates = ai_service._build_comparison_candidates(sample_ads[0])

    assert len(candidates) == 1
    assert candidates[0].price == 15.0
    assert candidates[0].source == "same_search"


def test_complete_json_falls_back_to_main_when_cheap_model_fails():
    """A broken cheap model must not stall the analyzer queue."""
    ai_service = AIService.__new__(AIService)
    ai_service.model = "main-model"
    ai_service.cheap_model = "broken-cheap-model"

    calls: list[str] = []

    def fake_chat_json(prompt, model, images, max_tokens):
        calls.append(model)
        if model == "broken-cheap-model":
            raise RuntimeError("model not found")
        return '{"ok": true}'

    ai_service._chat_json = fake_chat_json  # type: ignore[method-assign]
    result = ai_service._complete_json("prompt", "broken-cheap-model")

    assert result == '{"ok": true}'
    assert calls == ["broken-cheap-model", "main-model"]


def test_complete_json_propagates_main_model_failure():
    """If the main model itself fails the error must surface for the ErrorLog."""
    ai_service = AIService.__new__(AIService)
    ai_service.model = "main-model"
    ai_service.cheap_model = "main-model"

    def fake_chat_json(prompt, model, images, max_tokens):
        raise RuntimeError("upstream down")

    ai_service._chat_json = fake_chat_json  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="upstream down"):
        ai_service._complete_json("prompt", "main-model")


def test_analyze_ads_continues_when_rollback_connection_is_closed():
    """A dead DB connection in the error handler must not abort the whole batch."""

    class BrokenRollbackSession:
        def __init__(self) -> None:
            self.invalidated = 0
            self.closed = 0

        def rollback(self) -> None:
            raise SQLAlchemyError("connection already closed")

        def invalidate(self) -> None:
            self.invalidated += 1

        def close(self) -> None:
            self.closed += 1

    ai_service = AIService.__new__(AIService)
    ai_service.session = BrokenRollbackSession()

    calls: list[int | None] = []

    def fake_analyze_ad(ad: Ad, prompt_text: str) -> None:
        calls.append(ad.id)
        if ad.id == 1:
            raise RuntimeError("boom")

    ai_service._build_prompt_text_for_log = lambda ad: "prompt"  # type: ignore[method-assign]
    ai_service._analyze_ad = fake_analyze_ad  # type: ignore[method-assign]
    ai_service._log_analysis_error = lambda *args, **kwargs: None  # type: ignore[method-assign]

    ads = [
        Ad(owner_id="owner", id=1, external_id="1", title="Broken", url="https://example.com/1"),
        Ad(owner_id="owner", id=2, external_id="2", title="Works", url="https://example.com/2"),
    ]

    assert ai_service._analyze_ads(ads) == 1
    assert calls == [1, 2]
    assert ai_service.session.invalidated >= 1
    assert ai_service.session.closed >= 1


def test_apply_result_to_ad_persists_evidence(sample_ads):
    """Persisted ad fields keep the simple score plus explainable evidence."""
    ai_service = AIService.__new__(AIService)
    ad = sample_ads[1]
    product = ProductExtraction(product_key="rode podmic", is_specific_product=True)
    comparisons = [ComparisonCandidate(title="Rode PodMic", price=90)]
    judgements = [ComparisonJudgement(candidate_index=0, comparable=True, adjusted_price=90)]
    market = MarketEstimate(
        estimated_market_price=90,
        market_price_confidence=0.55,
        price_delta_percent=11.1,
        comparison_count=1,
        comparison_summary="Median aus 1 belastbaren Vergleichen: 90 EUR.",
    )
    final = FinalDealResult(
        score=6.5,
        summary="Etwas unter Marktwert.",
        reasoning="Der Preis liegt leicht unter einem belastbaren Vergleich.",
        estimated_market_price=90,
        market_price_confidence=0.55,
        price_delta_percent=11.1,
        comparison_summary=market.comparison_summary,
    )
    result = DealAnalysisResult(
        final=final,
        product=product,
        comparisons=comparisons,
        judgements=judgements,
        market=market,
        model_used="cheap-model",
        used_strong_model=False,
    )

    ai_service._apply_result_to_ad(ad, result)

    assert ad.bargain_score == 6.5
    assert ad.estimated_market_price == 90
    assert ad.market_price_confidence == 0.55
    assert ad.deal_evidence is not None
    assert ad.deal_evidence["model_used"] == "cheap-model"


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
    """Ohne ``prompt_addition`` kein Anweisungsblock im gerenderten Nutzerinhalt."""
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
