"""Fundgrube-Bewertung: hybrides Wert-gegen-Aufwand-Scoring für Verschenk-Anzeigen.

Bei Verschenken ist der Preis 0 — die Frage ist nicht „Rabatt", sondern „lohnt sich der
Aufwand für das, was ich bekomme?". Arbeitsteilung: **das LLM schätzt** semantisch
(Wiederverkaufswert, Zustand, Transportklasse, Interessens-Match), **eine Formel verrechnet**
deterministisch (Transport-Matrix × Distanz × Fahrzeug → Aufwand; Wert − Aufwand + Schwerpunkt-
Bonus → Score). Die Gewichte sind bewusst benannte Konstanten zum späteren Tunen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import exp
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, field_validator

from app.services.deal_analysis import (
    FinalDealResult,
    MarketEstimate,
    _coerce_unit_float,
)

# --- Literals ---------------------------------------------------------------
GiftTransportClass = Literal["pocket", "box", "two_person", "van_needed"]
GiftVehicle = Literal["bike", "small_car", "estate", "van"]
GiftInterestMatch = Literal["off_profile", "neutral", "on_focus"]
GiftRelevance = Literal["skip", "maybe", "candidate"]

# --- Scoring-Konstanten (Startwerte, bewusst benannt und tunebar) -----------
GIFT_VALUE_SCALE_EUR = 130.0  # Sättigung der Wertkurve: ~100€→5.4, ~200€→7.9, ~300€→9.0
GIFT_EFFORT_WEIGHT = 5.0  # max. Punktabzug durch Aufwand (effort 0..1)
GIFT_FOCUS_BOOST = 2.0  # Bonus bei Schwerpunkt-Treffer (on_focus)
GIFT_DISTANCE_MALUS = 0.4  # Anteil der Distanz am Aufwand (0..1)
GIFT_HEAVY_RELIEF = 0.6  # Faktor auf schwere Klassen, wenn can_carry_heavy
GIFT_CONFIDENCE_FLOOR = 0.6  # Restgewicht des Wertes bei value_confidence=0
GIFT_UNKNOWN_VALUE_SCORE = 2.0  # Wertscore ohne belastbare Wertschätzung
GIFT_DEFECT_VALUE_CAP = 2.0  # Wert-Deckel bei defektem Zustand

_DEFECT_CONDITIONS = {"defekt", "kaputt", "broken", "beschädigt", "beschaedigt", "defect"}

# Transport-Grundaufwand 0..1 je (Objektklasse × Fahrzeug); None = nicht transportierbar.
_TRANSPORT_EFFORT: dict[str, dict[str, float | None]] = {
    "pocket": {"bike": 0.05, "small_car": 0.0, "estate": 0.0, "van": 0.0},
    "box": {"bike": 0.40, "small_car": 0.15, "estate": 0.10, "van": 0.05},
    "two_person": {"bike": None, "small_car": 0.60, "estate": 0.35, "van": 0.15},
    "van_needed": {"bike": None, "small_car": None, "estate": 0.65, "van": 0.30},
}
_DEFAULT_TRANSPORT_EFFORT = 0.3


# --- Coercion helpers (billige Modelle liefern gern Freitext) ---------------
_TRANSPORT_KEYWORDS: tuple[tuple[str, GiftTransportClass], ...] = (
    ("hosentasche", "pocket"),
    ("pocket", "pocket"),
    ("klein", "pocket"),
    ("karton", "box"),
    ("box", "box"),
    ("kiste", "box"),
    ("zwei person", "two_person"),
    ("two_person", "two_person"),
    ("two person", "two_person"),
    ("sperrig", "two_person"),
    ("transporter", "van_needed"),
    ("van", "van_needed"),
    ("van_needed", "van_needed"),
    ("gross", "van_needed"),
    ("groß", "van_needed"),
)

_INTEREST_KEYWORDS: tuple[tuple[str, GiftInterestMatch], ...] = (
    ("on_focus", "on_focus"),
    ("schwerpunkt", "on_focus"),
    ("treffer", "on_focus"),
    ("focus", "on_focus"),
    ("off_profile", "off_profile"),
    ("uninteress", "off_profile"),
    ("passt nicht", "off_profile"),
    ("neutral", "neutral"),
)


def _coerce_literal(
    value: Any, keywords: tuple[tuple[str, Any], ...], valid: tuple[Any, ...], fallback: Any
) -> Any:
    """Bildet Freitext auf einen erlaubten Literal-Wert ab (sonst Fallback)."""
    if isinstance(value, str):
        text = value.strip().lower()
        if text in valid:
            return text
        for keyword, mapped in keywords:
            if keyword in text:
                return mapped
    return fallback


def _coerce_optional_eur(value: Any) -> float | None:
    """Best-effort-Zahl aus '50€' / 'ca. 50' / 50; None wenn nichts Sinnvolles."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value) if value >= 0 else None
    if not isinstance(value, str):
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", value)
    return float(match.group().replace(",", ".")) if match else None


# --- Structured output ------------------------------------------------------
class GiftAssessment(BaseModel):
    """LLM-Schätzung einer Verschenk-Anzeige (semantischer Teil des Scorings)."""

    estimated_value_eur: float | None = None
    value_confidence: float = Field(default=0.4, ge=0, le=1)
    condition: str | None = None
    transport_class: GiftTransportClass = "box"
    interest_match: GiftInterestMatch = "neutral"
    summary: str = ""
    reasoning: str = ""

    @field_validator("estimated_value_eur", mode="before")
    @classmethod
    def coerce_value(cls, value: Any) -> float | None:
        return _coerce_optional_eur(value)

    @field_validator("value_confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value: Any) -> float:
        return _coerce_unit_float(value)

    @field_validator("transport_class", mode="before")
    @classmethod
    def coerce_transport(cls, value: Any) -> GiftTransportClass:
        return _coerce_literal(
            value, _TRANSPORT_KEYWORDS, get_args(GiftTransportClass), "box"
        )

    @field_validator("interest_match", mode="before")
    @classmethod
    def coerce_interest(cls, value: Any) -> GiftInterestMatch:
        return _coerce_literal(
            value, _INTEREST_KEYWORDS, get_args(GiftInterestMatch), "neutral"
        )


def coerce_gift_relevance(value: Any) -> GiftRelevance:
    """Bildet die Nano-Gate-Antwort auf skip/maybe/candidate ab (im Zweifel maybe)."""
    keywords: tuple[tuple[str, GiftRelevance], ...] = (
        ("skip", "skip"),
        ("überspring", "skip"),
        ("ignor", "skip"),
        ("müll", "skip"),
        ("candidate", "candidate"),
        ("kandidat", "candidate"),
        ("treffer", "candidate"),
        ("maybe", "maybe"),
        ("vielleicht", "maybe"),
    )
    return _coerce_literal(value, keywords, get_args(GiftRelevance), "maybe")


# --- Deterministic effort + score -------------------------------------------
def compute_gift_effort(
    transport_class: str,
    vehicle: str,
    can_carry_heavy: bool,
    distance_km: float | None,
    radius_km: int | None,
) -> tuple[float, bool]:
    """Aufwand 0..1 und Machbarkeit aus Transport-Matrix × Distanz × Fahrzeug.

    ``feasible=False`` heißt: mit diesem Fahrzeug nicht transportierbar (Sofa aufs Fahrrad).
    """
    base = _TRANSPORT_EFFORT.get(transport_class, {}).get(vehicle, _DEFAULT_TRANSPORT_EFFORT)
    if base is None:
        return 1.0, False
    if can_carry_heavy and transport_class in ("two_person", "van_needed"):
        base *= GIFT_HEAVY_RELIEF
    dist_norm = 0.0
    if distance_km is not None and radius_km and radius_km > 0:
        dist_norm = min(distance_km / radius_km, 1.0)
    effort = min(1.0, base + GIFT_DISTANCE_MALUS * dist_norm)
    return effort, True


def _gift_value_score(
    value_eur: float | None, confidence: float, condition: str | None
) -> float:
    """Wertscore 0..10 (sättigend), gedeckelt bei Defekt, gedämpft durch Unsicherheit."""
    if value_eur is None or value_eur <= 0:
        base = GIFT_UNKNOWN_VALUE_SCORE
    else:
        base = 10.0 * (1.0 - exp(-value_eur / GIFT_VALUE_SCALE_EUR))
    if condition and condition.strip().lower() in _DEFECT_CONDITIONS:
        base = min(base, GIFT_DEFECT_VALUE_CAP)
    conf = max(0.0, min(1.0, confidence))
    damping = GIFT_CONFIDENCE_FLOOR + (1.0 - GIFT_CONFIDENCE_FLOOR) * conf
    return base * damping


def compute_gift_score(assessment: GiftAssessment, effort: float, feasible: bool) -> float:
    """Finaler Abhol-Lohn-Score 0..10: Wert − Aufwand + Schwerpunkt-Bonus."""
    if not feasible:
        return 0.0
    value_score = _gift_value_score(
        assessment.estimated_value_eur, assessment.value_confidence, assessment.condition
    )
    penalty = GIFT_EFFORT_WEIGHT * effort
    boost = GIFT_FOCUS_BOOST if assessment.interest_match == "on_focus" else 0.0
    return round(max(0.0, min(10.0, value_score - penalty + boost)), 1)


# --- Result object (duck-types DealAnalysisResult for the AI service) -------
@dataclass(frozen=True)
class GiftAnalysisResult:
    """Fundgrube-Bewertung; bietet dieselbe Schnittstelle wie ``DealAnalysisResult``."""

    final: FinalDealResult
    market: MarketEstimate
    assessment: GiftAssessment
    relevance: GiftRelevance
    effort: float
    feasible: bool
    distance_km: float | None
    model_used: str

    def evidence_json(self) -> dict[str, object]:
        """Erklärbare Evidenz für die Speicherung in ``Ad.deal_evidence``."""
        return {
            "mode": "gift_category",
            "assessment": self.assessment.model_dump(),
            "relevance": self.relevance,
            "effort": round(self.effort, 3),
            "feasible": self.feasible,
            "distance_km": self.distance_km,
            "model_used": self.model_used,
        }


def build_gift_result(
    assessment: GiftAssessment,
    *,
    relevance: GiftRelevance,
    distance_km: float | None,
    radius_km: int | None,
    vehicle: str,
    can_carry_heavy: bool,
    model_used: str,
) -> GiftAnalysisResult:
    """Verrechnet die LLM-Schätzung deterministisch zu Score + Ergebnisobjekt."""
    effort, feasible = compute_gift_effort(
        assessment.transport_class, vehicle, can_carry_heavy, distance_km, radius_km
    )
    score = compute_gift_score(assessment, effort, feasible)
    summary = assessment.summary or _default_summary(assessment, distance_km, feasible)
    market = MarketEstimate(
        estimated_market_price=assessment.estimated_value_eur,
        market_price_confidence=assessment.value_confidence,
        price_delta_percent=None,
        comparison_count=0,
        comparison_summary=summary,
    )
    final = FinalDealResult(
        score=score,
        summary=summary,
        reasoning=assessment.reasoning or summary,
        estimated_market_price=assessment.estimated_value_eur,
        market_price_confidence=assessment.value_confidence,
        price_delta_percent=None,
        comparison_summary=summary,
    )
    return GiftAnalysisResult(
        final=final,
        market=market,
        assessment=assessment,
        relevance=relevance,
        effort=effort,
        feasible=feasible,
        distance_km=distance_km,
        model_used=model_used,
    )


def _default_summary(
    assessment: GiftAssessment, distance_km: float | None, feasible: bool
) -> str:
    """Kompakte Karten-Zeile, falls das Modell keine summary liefert."""
    if not feasible:
        return "Mit dem angegebenen Fahrzeug kaum transportierbar."
    value = (
        f"≈{assessment.estimated_value_eur:.0f}€"
        if assessment.estimated_value_eur
        else "Wert unklar"
    )
    dist = f" · {distance_km:.0f} km" if distance_km is not None else ""
    return f"{value}{dist} · {assessment.transport_class}"


def fallback_gift_assessment(title: str) -> GiftAssessment:
    """Konservative Schätzung, wenn der Assessment-Call scheitert (Queue läuft weiter)."""
    return GiftAssessment(
        estimated_value_eur=None,
        value_confidence=0.2,
        condition=None,
        transport_class="box",
        interest_match="neutral",
        summary="Bewertung ohne KI-Antwort — Wert und Aufwand unsicher.",
        reasoning=(
            "Automatischer Fallback nach KI-Fehler. Ohne belastbare Wertschätzung bleibt "
            "der Fundgrube-Score bewusst niedrig."
        ),
    )


# --- Prompts ----------------------------------------------------------------
def build_gift_gate_prompt(context: dict[str, object]) -> str:
    """Billiges Vorfilter-Gate: skip/maybe/candidate über Titel + Kurzinfo (hoher Recall)."""
    profile = context.get("gift_interest_profile") or "kein Profil angegeben"
    focus = context.get("gift_focus_keywords") or "keine"
    return (
        "Du filterst Anzeigen aus der Kleinanzeigen-Kategorie 'Zu verschenken'. "
        "Entscheide grob, ob dieser Fund für den Nutzer interessant sein KÖNNTE. "
        "Sei großzügig: Im Zweifel 'maybe', niemals vorschnell 'skip'. "
        "Verwende 'skip' nur für klaren Müll, Werbung/Spam, Stellenanzeigen oder "
        "eindeutig Uninteressantes.\n\n"
        f"Interessensprofil des Nutzers: {profile}\n"
        f"Schwerpunkte: {focus}\n\n"
        "Antworte AUSSCHLIESSLICH als JSON: "
        '{"relevance": "skip"|"maybe"|"candidate", "reason": "kurz"}\n\n'
        f"Anzeige:\n{_gift_ad_brief(context)}"
    )


def build_gift_assessment_prompt(context: dict[str, object]) -> str:
    """Gründliche Bewertung: Wert, Zustand, Transportklasse, Interessens-Match als JSON."""
    profile = context.get("gift_interest_profile") or "kein Profil angegeben"
    focus = context.get("gift_focus_keywords") or "keine"
    return (
        "Bewerte diese Verschenk-Anzeige (Preis = 0€) für den Nutzer. Schätze den "
        "realistischen Wiederverkaufs-/Neuwert und wie aufwendig die Abholung ist.\n\n"
        f"Interessensprofil: {profile}\n"
        f"Schwerpunkte (Treffer = on_focus): {focus}\n\n"
        "Felder und erlaubte Werte:\n"
        "  - estimated_value_eur: number oder null (realistischer Wiederverkaufswert in EUR)\n"
        "  - value_confidence: number 0.0..1.0\n"
        "  - condition: kurzer String (z. B. 'gut', 'gebraucht', 'defekt') oder null\n"
        "  - transport_class: GENAU einer von 'pocket' (Hosentasche/Werkzeug), "
        "'box' (Karton/Mikrowelle), 'two_person' (Sessel/Waschmaschine), "
        "'van_needed' (Schrank/Sofa)\n"
        "  - interest_match: GENAU einer von 'off_profile', 'neutral', 'on_focus'\n"
        "  - summary: eine knappe Zeile für die Karte\n"
        "  - reasoning: kurze Begründung\n\n"
        "Antworte AUSSCHLIESSLICH als JSON-Objekt mit exakt diesen Feldern.\n\n"
        f"Anzeige:\n{_gift_ad_brief(context)}"
    )


def _gift_ad_brief(context: dict[str, object]) -> str:
    """Kompakte Anzeigen-Darstellung für die Gift-Prompts."""
    brief = {
        "title": context.get("title"),
        "description": context.get("description"),
        "condition": context.get("condition"),
        "location": context.get("location"),
        "distance_km": context.get("distance_km"),
    }
    return str({key: value for key, value in brief.items() if value is not None})
