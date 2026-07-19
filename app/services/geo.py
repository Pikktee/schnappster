"""Offline-Distanz (Luftlinie) zwischen deutschen Postleitzahlen.

Die PLZ-Zentroide stammen aus GeoNames (CC-BY 4.0) und wurden einmalig via ``pgeocode``
nach ``data/de_postal_centroids.csv.gz`` extrahiert. Die Laufzeit braucht dadurch weder
``pgeocode`` noch ``pandas`` — nur diese eine gebündelte Datei und reines Python.

Basis für die Aufwand-Achse der Fundgrube: „leicht abholbar" hängt an der Entfernung
zwischen Nutzer-PLZ und Anzeigen-PLZ.
"""

import gzip
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "data" / "de_postal_centroids.csv.gz"
_EARTH_RADIUS_KM = 6371.0
_PLZ_LENGTH = 5


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Luftlinie zwischen zwei Koordinaten (Dezimalgrad) in km via Haversine-Formel."""
    rlat1, rlon1, rlat2, rlon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * asin(sqrt(a))


@lru_cache(maxsize=1)
def _centroids() -> dict[str, tuple[float, float]]:
    """Lädt die gebündelte PLZ→(lat, lon)-Tabelle (einmalig, gecacht)."""
    table: dict[str, tuple[float, float]] = {}
    with gzip.open(_DATA_PATH, "rt", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split(",")
            if len(parts) != 3:
                continue
            plz, lat_text, lon_text = parts
            try:
                table[plz] = (float(lat_text), float(lon_text))
            except ValueError:
                continue
    return table


def normalize_plz(value: str | None) -> str | None:
    """Extrahiert eine 5-stellige deutsche PLZ aus freiem Text; None wenn keine vorhanden.

    Orts-Strings wie ``"10115 Berlin"`` tragen die PLZ als erste fünf Ziffern.
    """
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) < _PLZ_LENGTH:
        return None
    return digits[:_PLZ_LENGTH]


def coordinates_for(postal_code: str | None) -> tuple[float, float] | None:
    """Zentroid-Koordinaten einer deutschen PLZ, oder None wenn unbekannt."""
    plz = normalize_plz(postal_code)
    if plz is None:
        return None
    return _centroids().get(plz)


def postal_distance_km(plz_a: str | None, plz_b: str | None) -> float | None:
    """Luftlinie zwischen zwei deutschen PLZ in km; None, wenn eine PLZ unbekannt ist."""
    coord_a = coordinates_for(plz_a)
    coord_b = coordinates_for(plz_b)
    if coord_a is None or coord_b is None:
        return None
    return round(haversine_km(coord_a[0], coord_a[1], coord_b[0], coord_b[1]), 1)
