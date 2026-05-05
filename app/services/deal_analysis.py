"""Evidence-based bargain analysis helpers.

The module keeps the deal logic small and testable. LLM calls live in
``AIService``; this file owns structured outputs, prompt payloads and the
deterministic scoring/evidence math around them.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_SEARCH_QUERIES = 5
MAX_REASON_LEN = 180
MARKET_PRICE_OUTLIER_LOW = 0.45
MARKET_PRICE_OUTLIER_HIGH = 2.2
BASE_CONFIDENCE = 0.35
CONFIDENCE_PER_COMPARISON = 0.08
SPECIFIC_PRODUCT_CONFIDENCE_BONUS = 0.12
MAX_MARKET_CONFIDENCE = 0.9


class ProductExtraction(BaseModel):
    """Structured understanding of the target ad."""

    product_key: str = ""
    category: str | None = None
    search_queries: list[str] = Field(default_factory=list)
    is_specific_product: bool = False
    deal_potential: float = Field(default=0.0, ge=0, le=1)
    uncertainty: str | None = None

    @field_validator("search_queries")
    @classmethod
    def limit_queries(cls, queries: list[str]) -> list[str]:
        """Keep downstream search/tool usage bounded."""
        cleaned = [query.strip() for query in queries if query.strip()]
        return cleaned[:MAX_SEARCH_QUERIES]


class ComparisonCandidate(BaseModel):
    """A comparison ad available to the analysis pipeline."""

    id: int | None = None
    title: str
    price: float
    condition: str | None = None
    source: str = "same_search"


ComparisonRelation = Literal["same", "better", "worse", "bundle", "accessory", "unknown"]


class ComparisonJudgement(BaseModel):
    """LLM judgement of how usable one comparison candidate is."""

    candidate_index: int
    comparable: bool
    relation: ComparisonRelation = "unknown"
    adjusted_price: float | None = Field(default=None, ge=0)
    reason: str = ""

    @field_validator("reason")
    @classmethod
    def shorten_reason(cls, reason: str) -> str:
        """Avoid storing verbose per-comparison explanations."""
        text = reason.strip()
        return text[:MAX_REASON_LEN]


class MarketEstimate(BaseModel):
    """Deterministic market-value estimate built from accepted comparisons."""

    estimated_market_price: float | None
    market_price_confidence: float
    price_delta_percent: float | None
    comparison_count: int
    comparison_summary: str


class FinalDealResult(BaseModel):
    """Final score and user-facing explanation."""

    score: float = Field(ge=0, le=10)
    summary: str
    reasoning: str
    estimated_market_price: float | None = None
    market_price_confidence: float = Field(default=0.0, ge=0, le=1)
    price_delta_percent: float | None = None
    comparison_summary: str | None = None


@dataclass(frozen=True)
class DealAnalysisResult:
    """Full result persisted after one ad analysis."""

    final: FinalDealResult
    product: ProductExtraction
    comparisons: list[ComparisonCandidate]
    judgements: list[ComparisonJudgement]
    market: MarketEstimate
    model_used: str
    used_strong_model: bool

    def evidence_json(self) -> dict[str, object]:
        """Serialize the explainable evidence for storage."""
        return {
            "product": self.product.model_dump(),
            "comparisons": [candidate.model_dump() for candidate in self.comparisons],
            "judgements": [judgement.model_dump() for judgement in self.judgements],
            "market": self.market.model_dump(),
            "model_used": self.model_used,
            "used_strong_model": self.used_strong_model,
        }


def build_market_estimate(
    ad_price: float | None,
    product: ProductExtraction,
    candidates: list[ComparisonCandidate],
    judgements: list[ComparisonJudgement],
) -> MarketEstimate:
    """Estimate market value from comparable candidate prices."""
    prices = _accepted_prices(candidates, judgements)
    filtered_prices = _remove_outliers(prices)
    if not filtered_prices:
        return MarketEstimate(
            estimated_market_price=None,
            market_price_confidence=0.0,
            price_delta_percent=None,
            comparison_count=0,
            comparison_summary="Keine belastbaren Vergleichsangebote.",
        )

    market_price = float(round(median(filtered_prices), 2))
    confidence = _market_confidence(len(filtered_prices), product.is_specific_product)
    delta = _price_delta_percent(ad_price, market_price)
    return MarketEstimate(
        estimated_market_price=market_price,
        market_price_confidence=confidence,
        price_delta_percent=delta,
        comparison_count=len(filtered_prices),
        comparison_summary=_comparison_summary(market_price, filtered_prices),
    )


def should_use_strong_model(
    market: MarketEstimate,
    min_delta_percent: float,
    min_savings_eur: float,
    ad_price: float | None,
) -> bool:
    """Reserve the stronger model for likely bargains with enough evidence."""
    if ad_price is None or market.estimated_market_price is None:
        return False
    delta = market.price_delta_percent or 0.0
    savings = market.estimated_market_price - ad_price
    return delta >= min_delta_percent or savings >= min_savings_eur


def fallback_product_extraction(title: str) -> ProductExtraction:
    """Conservative fallback when the cheap product extraction call fails."""
    query = " ".join(title.split()[:6])
    return ProductExtraction(
        product_key=query.lower(),
        category=None,
        search_queries=[query] if query else [],
        is_specific_product=False,
        deal_potential=0.0,
        uncertainty="Automatischer Fallback ohne sichere Produkterkennung.",
    )


def fallback_final_result(market: MarketEstimate) -> FinalDealResult:
    """Deterministic last-resort score when every LLM call in the pipeline fails."""
    delta = market.price_delta_percent
    if delta is None:
        score = 5.0
        summary = "Bewertung ohne KI-Antwort: kein belastbarer Marktwert."
    else:
        score = max(0.0, min(10.0, 5.0 + delta / 8.0))
        summary = (
            f"Bewertung ohne KI-Antwort: Preis liegt {delta:.0f}% unter geschätztem Marktwert."
        )
    return FinalDealResult(
        score=round(score, 1),
        summary=summary,
        reasoning=(
            "Automatischer Fallback nach KI-Fehler. Score basiert allein auf dem "
            "deterministischen Marktwert-Vergleich, nicht auf einer Modell-Antwort."
        ),
        estimated_market_price=market.estimated_market_price,
        market_price_confidence=market.market_price_confidence,
        price_delta_percent=market.price_delta_percent,
        comparison_summary=market.comparison_summary,
    )


def fallback_comparison_judgements(
    candidates: list[ComparisonCandidate],
) -> list[ComparisonJudgement]:
    """Use same-search prices as weak evidence if the comparison judge fails."""
    return [
        ComparisonJudgement(
            candidate_index=index,
            comparable=True,
            relation="unknown",
            adjusted_price=candidate.price,
            reason="Fallback: Vergleich aus derselben Suche.",
        )
        for index, candidate in enumerate(candidates)
    ]


def build_product_prompt(target: dict[str, object]) -> str:
    """Prompt for the low-cost product analyst."""
    return (
        "Analysiere diese Kleinanzeigen-Anzeige als Product Analyst. "
        "Extrahiere, was verglichen werden muss, um den Marktwert zu bestimmen. "
        "Antworte ausschliesslich als JSON mit den Feldern product_key, category, "
        "search_queries, is_specific_product, deal_potential, uncertainty.\n\n"
        f"Anzeige:\n{target}"
    )


def build_comparison_prompt(
    target: dict[str, object],
    product: ProductExtraction,
    candidates: list[ComparisonCandidate],
) -> str:
    """Prompt for judging whether comparison candidates are usable."""
    return (
        "Bewerte Vergleichsangebote fuer eine Kleinanzeigen-Schaetzung. "
        "Markiere nur echte Vergleichbarkeit als comparable=true. Zubehör, Defekte, "
        "andere Varianten oder Bundles muessen entsprechend abgewertet werden. "
        "Antworte ausschliesslich als JSON-Array mit candidate_index, comparable, "
        "relation, adjusted_price, reason.\n\n"
        f"Zielanzeige:\n{target}\n\n"
        f"Produktverstaendnis:\n{product.model_dump()}\n\n"
        f"Vergleichskandidaten:\n{[candidate.model_dump() for candidate in candidates]}"
    )


def build_final_prompt(
    target: dict[str, object],
    product: ProductExtraction,
    market: MarketEstimate,
    judgements: list[ComparisonJudgement],
) -> str:
    """Prompt for the final compact deal score."""
    return (
        "Erzeuge den finalen Schnappchen-Score fuer diese Kleinanzeigen-Anzeige. "
        "Der Marktpreis ist der wichtigste Faktor. Sei konservativ: 5 ist normal, "
        "7 ist ein gutes Angebot, 8-9 ein seltenes echtes Schnappchen, 10 fast nie. "
        "Nutze Unsicherheit und Vergleichbarkeit, um den Score zu senken. "
        "Antworte ausschliesslich im JSON-Format mit score, summary, reasoning, "
        "estimated_market_price, market_price_confidence, price_delta_percent, "
        "comparison_summary.\n\n"
        f"Zielanzeige:\n{target}\n\n"
        f"Produktverstaendnis:\n{product.model_dump()}\n\n"
        f"Marktwertschaetzung:\n{market.model_dump()}\n\n"
        f"Vergleichsurteile:\n{[judgement.model_dump() for judgement in judgements]}"
    )


def _accepted_prices(
    candidates: list[ComparisonCandidate],
    judgements: list[ComparisonJudgement],
) -> list[float]:
    accepted: list[float] = []
    for judgement in judgements:
        if not judgement.comparable:
            continue
        price = judgement.adjusted_price or _candidate_price(candidates, judgement.candidate_index)
        if price and price > 0:
            accepted.append(float(price))
    return accepted


def _candidate_price(candidates: list[ComparisonCandidate], index: int) -> float | None:
    if index < 0 or index >= len(candidates):
        return None
    return candidates[index].price


def _remove_outliers(prices: list[float]) -> list[float]:
    if len(prices) < 4:
        return prices
    center = median(prices)
    low = center * MARKET_PRICE_OUTLIER_LOW
    high = center * MARKET_PRICE_OUTLIER_HIGH
    filtered = [price for price in prices if low <= price <= high]
    return filtered or prices


def _market_confidence(count: int, is_specific_product: bool) -> float:
    confidence = BASE_CONFIDENCE + count * CONFIDENCE_PER_COMPARISON
    if is_specific_product:
        confidence += SPECIFIC_PRODUCT_CONFIDENCE_BONUS
    return min(MAX_MARKET_CONFIDENCE, round(confidence, 2))


def _price_delta_percent(ad_price: float | None, market_price: float) -> float | None:
    if ad_price is None or market_price <= 0:
        return None
    return round(((market_price - ad_price) / market_price) * 100, 1)


def _comparison_summary(market_price: float, prices: list[float]) -> str:
    price_text = ", ".join(f"{price:.0f} EUR" for price in sorted(prices))
    return (
        f"Median aus {len(prices)} belastbaren Vergleichen: {market_price:.0f} EUR ({price_text})."
    )
