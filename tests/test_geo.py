"""Tests für die PLZ-Distanz (Luftlinie) der Fundgrube-Aufwand-Achse."""

from app.services.geo import (
    coordinates_for,
    haversine_km,
    normalize_plz,
    postal_distance_km,
)


class TestHaversine:
    def test_zero_distance_for_identical_points(self):
        assert haversine_km(52.52, 13.40, 52.52, 13.40) == 0.0

    def test_berlin_munich_air_line(self):
        # Berlin ↔ München beträgt Luftlinie ~504 km.
        distance = haversine_km(52.52, 13.40, 48.14, 11.57)
        assert 495 <= distance <= 515


class TestNormalizePlz:
    def test_plain_five_digit_code(self):
        assert normalize_plz("10115") == "10115"

    def test_extracts_from_location_string(self):
        assert normalize_plz("10115 Berlin") == "10115"

    def test_keeps_leading_zero(self):
        assert normalize_plz("01067 Dresden") == "01067"

    def test_returns_none_for_too_short(self):
        assert normalize_plz("123") is None

    def test_returns_none_for_empty(self):
        assert normalize_plz(None) is None
        assert normalize_plz("") is None


class TestPostalDistance:
    def test_known_cities(self):
        # Berlin (10115) ↔ München (80331) ~504 km über die gebündelten Zentroide.
        distance = postal_distance_km("10115", "80331")
        assert distance is not None
        assert 490 <= distance <= 520

    def test_same_postal_code_is_zero(self):
        assert postal_distance_km("50667", "50667") == 0.0

    def test_nearby_codes_are_close(self):
        # Zwei Kölner PLZ liegen wenige Kilometer auseinander.
        distance = postal_distance_km("50667", "50823")
        assert distance is not None
        assert 0 <= distance <= 15

    def test_unknown_code_returns_none(self):
        assert postal_distance_km("99999xyz", "10115") is None
        assert postal_distance_km("10115", None) is None

    def test_accepts_location_strings(self):
        distance = postal_distance_km("10115 Berlin", "80331 München")
        assert distance is not None
        assert 490 <= distance <= 520


class TestCoordinatesFor:
    def test_returns_tuple_for_known_code(self):
        coords = coordinates_for("10115")
        assert coords is not None
        lat, lon = coords
        assert 52 <= lat <= 53
        assert 13 <= lon <= 14

    def test_returns_none_for_unknown(self):
        assert coordinates_for("00000") is None
