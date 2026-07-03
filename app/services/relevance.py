"""Titel-Relevanz-Filter: Schutz gegen serverseitiges Fuzzy-Matching der Quellen.

eBay und MyDealz füllen die Trefferliste bei seltenen Suchbegriffen mit lose passenden
Angeboten auf (eBay: Abschnitt "Ergebnisse, die weniger Wörtern entsprechen"; MyDealz:
unscharfe Volltextsuche). Über URL-Parameter lässt sich das nicht zuverlässig abstellen,
daher filtern wir nach dem Parsen: ein Treffer bleibt nur, wenn **alle** Suchbegriff-Tokens
im Titel vorkommen — Umlaute gefaltet und leerzeichen-tolerant, sodass "tourbox" auch
"Tour Box" matcht. Ohne Suchbegriff (rein URL-basierte Suche) wird nicht gefiltert.
"""

# Umlaute falten wie im URL-Slug, damit "groesse" und "Größe" gleich normalisieren.
_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# Einzelne Buchstaben/Ziffern sind kein sinnvolles Relevanz-Signal (z.B. "x" in "x8 Pokémon").
_MIN_TOKEN_LEN = 2


def _normalize(text: str) -> str:
    """Lowercase + Umlaute falten (konsistent zum URL-Slug)."""
    return text.lower().translate(_UMLAUTS)


def _query_tokens(query: str) -> list[str]:
    """Zerlegt den Suchbegriff in bedeutungstragende Tokens (kurze/leere entfallen)."""
    return [token for token in _normalize(query).split() if len(token) >= _MIN_TOKEN_LEN]


def title_matches_query(title: str, query: str | None) -> bool:
    """True, wenn jedes Suchbegriff-Token im Titel steckt (leerzeichen-tolerant).

    Ohne Suchbegriff (URL-basierte Suche) immer True — dann gibt es keinen Begriff zu prüfen.
    Leerzeichen im Titel werden ignoriert, damit "tourbox" auch "Tour Box" trifft.
    """
    tokens = _query_tokens(query or "")
    if not tokens:
        return True
    haystack = _normalize(title).replace(" ", "")
    return all(token in haystack for token in tokens)
