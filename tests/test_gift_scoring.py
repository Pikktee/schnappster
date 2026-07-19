"""Tests für die deterministische Fundgrube-Bewertung (Transport-Matrix + Wert/Aufwand-Formel)."""

from app.services.gift_analysis import (
    GiftAssessment,
    coerce_gift_relevance,
    compute_gift_effort,
    compute_gift_score,
)


def _assess(**kwargs) -> GiftAssessment:
    return GiftAssessment(**kwargs)


class TestTransportEffort:
    def test_pocket_is_effortless_in_any_car(self):
        effort, feasible = compute_gift_effort("pocket", "small_car", False, 0, 10)
        assert feasible
        assert effort < 0.1

    def test_sofa_on_bike_is_infeasible(self):
        effort, feasible = compute_gift_effort("van_needed", "bike", False, 1, 10)
        assert feasible is False

    def test_two_person_in_small_car_is_feasible_but_hard(self):
        effort, feasible = compute_gift_effort("two_person", "small_car", False, 0, 10)
        assert feasible
        assert effort > 0.4

    def test_van_makes_bulky_easier(self):
        small_car = compute_gift_effort("van_needed", "estate", False, 0, 10)[0]
        van = compute_gift_effort("van_needed", "van", False, 0, 10)[0]
        assert van < small_car

    def test_can_carry_heavy_reduces_effort(self):
        without = compute_gift_effort("two_person", "small_car", False, 0, 10)[0]
        with_help = compute_gift_effort("two_person", "small_car", True, 0, 10)[0]
        assert with_help < without

    def test_distance_increases_effort(self):
        near = compute_gift_effort("box", "small_car", False, 1, 20)[0]
        far = compute_gift_effort("box", "small_car", False, 19, 20)[0]
        assert far > near

    def test_unknown_distance_has_no_distance_malus(self):
        effort, feasible = compute_gift_effort("box", "small_car", False, None, 10)
        assert feasible
        # Ohne Distanz nur der Transport-Grundaufwand, kein Distanz-Aufschlag.
        assert effort == compute_gift_effort("box", "small_car", False, 0, 10)[0]


class TestGiftScore:
    def test_infeasible_scores_zero(self):
        score = compute_gift_score(
            _assess(estimated_value_eur=500, value_confidence=0.9), effort=1.0, feasible=False
        )
        assert score == 0.0

    def test_higher_value_scores_higher(self):
        low = compute_gift_score(_assess(estimated_value_eur=20, value_confidence=0.8), 0.1, True)
        high = compute_gift_score(_assess(estimated_value_eur=250, value_confidence=0.8), 0.1, True)
        assert high > low

    def test_more_effort_scores_lower(self):
        easy = compute_gift_score(_assess(estimated_value_eur=150, value_confidence=0.8), 0.1, True)
        hard = compute_gift_score(_assess(estimated_value_eur=150, value_confidence=0.8), 0.9, True)
        assert easy > hard

    def test_focus_match_adds_boost(self):
        neutral = compute_gift_score(
            _assess(estimated_value_eur=120, value_confidence=0.8, interest_match="neutral"),
            0.2,
            True,
        )
        on_focus = compute_gift_score(
            _assess(estimated_value_eur=120, value_confidence=0.8, interest_match="on_focus"),
            0.2,
            True,
        )
        assert on_focus > neutral

    def test_defect_caps_value(self):
        good = compute_gift_score(
            _assess(estimated_value_eur=300, value_confidence=0.8, condition="gut"), 0.1, True
        )
        defect = compute_gift_score(
            _assess(estimated_value_eur=300, value_confidence=0.8, condition="defekt"), 0.1, True
        )
        assert defect < good

    def test_valuable_easy_focus_scores_high(self):
        # „Richtig tolle Sache": wertvoll, leicht abholbar, im Schwerpunkt → klar hoch.
        score = compute_gift_score(
            _assess(
                estimated_value_eur=250,
                value_confidence=0.85,
                transport_class="pocket",
                interest_match="on_focus",
            ),
            effort=0.05,
            feasible=True,
        )
        assert score >= 7.0

    def test_low_value_junk_scores_low(self):
        score = compute_gift_score(
            _assess(estimated_value_eur=5, value_confidence=0.6), effort=0.4, feasible=True
        )
        assert score <= 2.0

    def test_score_always_within_bounds(self):
        for value in (0, 10, 50, 500, 5000):
            for effort in (0.0, 0.5, 1.0):
                score = compute_gift_score(
                    _assess(estimated_value_eur=value, value_confidence=1.0), effort, True
                )
                assert 0.0 <= score <= 10.0


class TestCoercion:
    def test_relevance_defaults_to_maybe_when_unclear(self):
        assert coerce_gift_relevance("hmm keine ahnung") == "maybe"

    def test_relevance_maps_keywords(self):
        assert coerce_gift_relevance("SKIP das ist Müll") == "skip"
        assert coerce_gift_relevance("klarer Kandidat") == "candidate"
        assert coerce_gift_relevance("vielleicht") == "maybe"

    def test_assessment_coerces_freeform_transport(self):
        a = GiftAssessment.model_validate({"transport_class": "großer Karton"})
        assert a.transport_class == "box"

    def test_assessment_coerces_value_string(self):
        a = GiftAssessment.model_validate({"estimated_value_eur": "ca. 50€"})
        assert a.estimated_value_eur == 50.0

    def test_assessment_coerces_qualitative_confidence(self):
        a = GiftAssessment.model_validate({"value_confidence": "hoch"})
        assert a.value_confidence >= 0.7

    def test_assessment_invalid_interest_falls_back_neutral(self):
        a = GiftAssessment.model_validate({"interest_match": "weiß nicht"})
        assert a.interest_match == "neutral"
