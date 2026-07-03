"""Tests für den Titel-Relevanz-Filter (Schutz gegen eBay/MyDealz-Fuzzy-Matching)."""

import pytest

from app.services.relevance import title_matches_query


@pytest.mark.parametrize(
    "title",
    [
        "TourBox Elite Bluetooth Controller",
        "Tour Box Elite – neuwertig",  # leerzeichen-tolerant: "tourbox" trifft "Tour Box"
        "tourbox elite schwarz OVP",
        "Elite Controller TourBox für Kreative",  # Reihenfolge egal
    ],
)
def test_keeps_relevant_titles(title: str) -> None:
    assert title_matches_query(title, "tourbox elite") is True


@pytest.mark.parametrize(
    "title",
    [
        "Innentasche für Harley Davidson Top Case Top Box",  # nur "box"
        "Pokémon Astral Radiance Elite Trainer Box",  # nur "elite" + "box", kein "tourbox"
        "x8 Pokémon TCG: Chaos Rising Pokemon Center Elite Trainer Box",
        "Pokemon Sonne & Mond Base Lunala Elite Trainer Box Sealed",
    ],
)
def test_drops_irrelevant_titles(title: str) -> None:
    assert title_matches_query(title, "tourbox elite") is False


def test_no_query_keeps_everything() -> None:
    # Rein URL-basierte Suche: kein Begriff zu prüfen → nicht filtern.
    assert title_matches_query("Irgendein Angebot", None) is True
    assert title_matches_query("Irgendein Angebot", "   ") is True


def test_umlauts_are_folded() -> None:
    assert title_matches_query("Große Kühlbox", "grosse kuehlbox") is True
    assert title_matches_query("Grosse Kuehlbox", "große kühlbox") is True


def test_short_tokens_are_ignored() -> None:
    # "x" (1 Zeichen) ist kein Relevanz-Signal; "pokemon" muss aber passen.
    assert title_matches_query("Pokemon Sammlung", "x pokemon") is True
    assert title_matches_query("Nintendo Sammlung", "x pokemon") is False


def test_all_tokens_required() -> None:
    assert title_matches_query("LEGO Millennium Falcon", "lego falcon") is True
    assert title_matches_query("LEGO Star Destroyer", "lego falcon") is False
