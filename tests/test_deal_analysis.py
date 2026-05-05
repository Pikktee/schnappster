"""Tests for the evidence-based deal analysis helpers."""

from app.services.deal_analysis import (
    ComparisonCandidate,
    ComparisonJudgement,
    ProductExtraction,
    build_market_estimate,
    fallback_comparison_judgements,
    fallback_product_extraction,
    should_use_strong_model,
)


def test_build_market_estimate_uses_comparable_adjusted_prices():
    """Market value uses only accepted comparisons and computes the target delta."""
    product = ProductExtraction(product_key="rode podmic", is_specific_product=True)
    candidates = [
        ComparisonCandidate(title="Rode PodMic", price=80),
        ComparisonCandidate(title="Rode PodMic gebraucht", price=90),
        ComparisonCandidate(title="Rode PodMic defekt", price=20),
    ]
    judgements = [
        ComparisonJudgement(candidate_index=0, comparable=True, adjusted_price=80),
        ComparisonJudgement(candidate_index=1, comparable=True, adjusted_price=90),
        ComparisonJudgement(candidate_index=2, comparable=False, relation="worse"),
    ]

    estimate = build_market_estimate(55, product, candidates, judgements)

    assert estimate.estimated_market_price == 85
    assert estimate.price_delta_percent == 35.3
    assert estimate.comparison_count == 2
    assert estimate.market_price_confidence > 0.5


def test_build_market_estimate_filters_large_outliers():
    """One extreme candidate does not dominate the market median."""
    product = ProductExtraction(product_key="camera lens", is_specific_product=True)
    candidates = [
        ComparisonCandidate(title="Lens A", price=180),
        ComparisonCandidate(title="Lens B", price=190),
        ComparisonCandidate(title="Lens C", price=200),
        ComparisonCandidate(title="Lens fantasy price", price=900),
    ]
    judgements = fallback_comparison_judgements(candidates)

    estimate = build_market_estimate(120, product, candidates, judgements)

    assert estimate.estimated_market_price == 190
    assert estimate.comparison_count == 3


def test_should_use_strong_model_only_for_likely_deals():
    """The expensive model is reserved for high-delta candidates."""
    product = ProductExtraction(product_key="macbook", is_specific_product=True)
    candidates = [ComparisonCandidate(title="MacBook Vergleich", price=1000)]
    judgements = fallback_comparison_judgements(candidates)
    estimate = build_market_estimate(760, product, candidates, judgements)

    assert should_use_strong_model(estimate, 18, 75, 760)
    assert not should_use_strong_model(estimate, 30, 500, 760)


def test_fallback_product_extraction_limits_query_size():
    """Fallback extraction stays cheap and bounded."""
    product = fallback_product_extraction("Apple MacBook Pro 14 M1 Pro 16GB 512GB Space Grau")

    assert product.product_key == "apple macbook pro 14 m1 pro"
    assert product.search_queries == ["Apple MacBook Pro 14 M1 Pro"]
    assert not product.is_specific_product
