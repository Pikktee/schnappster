"""Preis-Extraktion aus beliebigem Webseiten-HTML.

Zwei Aufgaben:
- ``extract_candidates``: beim Anlegen mögliche Preisangaben vorschlagen (für die Auswahl).
- ``extract_price``: beim Monitoring den gewählten Preis per gespeichertem Locator wiederfinden.

Strategie (robust + billig, kein KI-Call beim Monitoring): strukturierte SEO-Daten
(JSON-LD, Microdata/OpenGraph-Meta) zuerst, sichtbarer Text als Fallback.
"""

import json
import logging
import re
from collections import Counter

from bs4 import BeautifulSoup, Tag
from openai import OpenAI  # pyright: ignore[reportMissingImports]

from app.core import config as app_config
from app.models.price_watch import PriceCandidate
from app.prompts.pricecandidates import (
    render_pricecandidates_system_prompt,
    render_pricecandidates_user_prompt,
)

logger = logging.getLogger(__name__)

# Währungssymbole → ISO-Code.
_CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP", "¥": "JPY"}
_CURRENCY_CODES = ("EUR", "USD", "GBP", "CHF", "JPY", "PLN")
# Vollständige Preisangabe mit Währung (für die Erkennung sichtbarer Preise).
_PRICE_WITH_CURRENCY = re.compile(
    r"(€|\$|£|¥|EUR|USD|GBP|CHF|JPY|PLN)\s?\d|\d[\d.,\s]*\s?(€|\$|£|¥|EUR|USD|GBP|CHF|JPY|PLN)",
    re.IGNORECASE,
)
_PRICE_KEYS = ("price", "lowprice", "highprice")
_MAX_VISIBLE_TEXT_LEN = 30
_MAX_CANDIDATES = 8
# Klassenfragmente, die einen Vorfahren als Preis-Container ausweisen (für eindeutige Selektoren).
_SEMANTIC_ANCHOR_KEYS = ("price", "amount", "cost", "offer", "deal", "pricetopay")
# Wie viele Vorfahren-Ebenen für die Selektor-Disambiguierung maximal geprüft werden.
_MAX_ANCESTOR_CLIMB = 6

# --- Prominenz-Scoring: welcher Kandidat ist der wahrscheinliche Hauptpreis? ---
# Strukturierte Daten (JSON-LD/Meta) sind der kanonische Hauptpreis → hoher Sockel; ein
# sichtbarer Preis im Kaufbereich (Buy-Box) wird geboostet, Streich-/Ratenpreise abgewertet.
_SCORE_JSONLD = 100.0
_SCORE_META = 90.0
_SCORE_VISIBLE_BASE = 40.0
_SCORE_MAIN_CONTAINER_BOOST = 45.0
_SCORE_SECONDARY_PENALTY = 60.0
# id-/Klassenfragmente, die den Kaufbereich (Hauptpreis) markieren — klein geschrieben.
_MAIN_PRICE_HINTS = (
    "pricetopay", "apexprice", "coreprice", "priceblock", "buybox",
    "dealprice", "ourprice", "price-current", "current-price", "product-price",
)
# ... die einen Nebenpreis markieren (Streichpreis/UVP/alter Preis).
_STRIKE_HINTS = (
    "a-text-price", "basisprice", "listprice", "list-price", "strikethrough",
    "was-price", "old-price", "uvp", "rrp",
)
# Sichtbarer Text, der eine Monatsrate verrät (kein Hauptpreis; steht meist im Preistext selbst).
_RATE_TEXT = re.compile(r"/\s*monat|/\s*mo\b|\bmtl\.?|monatlich", re.IGNORECASE)
# Sichtbarer Text, der einen Streich-/Listenpreis verrät (auch wenn er in einem Preis-Container
# steht) — z. B. "UVP: 54,99 €", "RRP: …", "statt 99 €".
_STRIKE_TEXT = re.compile(r"\b(uvp|rrp|statt|liste[nm]?preis|früher)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Preis-Parsing (generisch: deutsch 1.234,56 € und US $1,234.56)
# ---------------------------------------------------------------------------
def parse_price_value(text: str) -> tuple[float | None, str | None]:
    """Parst Betrag und Währung aus einem Preistext; (None, ...) wenn nicht parsebar."""
    if not text:
        return None, None
    currency = _detect_currency(text)
    num = re.sub(r"[^\d.,]", "", text)
    if not num or not any(ch.isdigit() for ch in num):
        return None, currency
    num = _normalize_decimal(num)
    try:
        return float(num), currency
    except ValueError:
        return None, currency


def _detect_currency(text: str) -> str | None:
    """Erkennt Währung an Symbol oder ISO-Code im Text."""
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in text:
            return code
    upper = text.upper()
    for code in _CURRENCY_CODES:
        if code in upper:
            return code
    return None


def _normalize_decimal(num: str) -> str:
    """Vereinheitlicht Tausender-/Dezimaltrenner zu einem float-parsebaren String."""
    if "," in num and "." in num:
        # Letztes Trennzeichen ist der Dezimaltrenner.
        if num.rfind(",") > num.rfind("."):
            return num.replace(".", "").replace(",", ".")
        return num.replace(",", "")
    if "," in num:
        # Nur Komma: Dezimaltrenner bei genau 2 Nachkommastellen, sonst Tausender.
        if re.search(r",\d{2}$", num):
            return num.replace(",", ".")
        return num.replace(",", "")
    return num


# ---------------------------------------------------------------------------
# Kandidaten-Extraktion (beim Anlegen)
# ---------------------------------------------------------------------------
def extract_candidates(html: str) -> list[PriceCandidate]:
    """Sammelt mögliche Preisangaben aus dem HTML (strukturiert + sichtbar), dedupliziert."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    candidates = _extract_jsonld(soup) + _extract_meta(soup) + _extract_visible(soup)
    return _dedupe_and_rank(candidates)


def parse_title(html: str) -> str | None:
    """Liest den Seitentitel (<title> oder og:title) für einen sinnvollen Default-Namen."""
    soup = BeautifulSoup(html, "html.parser")
    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        return str(og["content"]).strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None


def _extract_jsonld(soup: BeautifulSoup) -> list[PriceCandidate]:
    """Extrahiert Preise aus <script type='application/ld+json'>-Blöcken."""
    out: list[PriceCandidate] = []
    for script_index, script in enumerate(soup.find_all("script", type="application/ld+json")):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        hits: list[tuple[list, float, str | None]] = []
        _walk_jsonld(data, [], hits)
        for path, value, currency in hits:
            out.append(
                PriceCandidate(
                    value=value,
                    currency=currency,
                    label="Preis",
                    source="jsonld",
                    locator={"strategy": "jsonld", "script_index": script_index, "path": path},
                    raw=f"{value}{(' ' + currency) if currency else ''}",
                    score=_SCORE_JSONLD,
                )
            )
    return out


def _walk_jsonld(obj: object, path: list, hits: list) -> None:
    """Sucht rekursiv nach price/lowPrice/highPrice (+ priceCurrency) in JSON-LD."""
    if isinstance(obj, dict):
        currency = obj.get("priceCurrency") if isinstance(obj.get("priceCurrency"), str) else None
        for key in _PRICE_KEYS:
            if key in obj and isinstance(obj[key], str | int | float):
                value, parsed_cur = parse_price_value(str(obj[key]))
                if value is not None:
                    hits.append((path + [key], value, currency or parsed_cur))
        for key, val in obj.items():
            _walk_jsonld(val, path + [key], hits)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            _walk_jsonld(val, path + [i], hits)


def _extract_meta(soup: BeautifulSoup) -> list[PriceCandidate]:
    """Extrahiert Preise aus Microdata-/OpenGraph-Meta-Tags."""
    out: list[PriceCandidate] = []
    selectors = (
        "meta[itemprop=price]",
        'meta[property="product:price:amount"]',
        'meta[property="og:price:amount"]',
    )
    currency_el = soup.select_one(
        "meta[itemprop=priceCurrency], "
        'meta[property="product:price:currency"], '
        'meta[property="og:price:currency"]'
    )
    meta_currency = str(currency_el["content"]).strip() if currency_el else None
    for selector in selectors:
        for el in soup.select(selector):
            value, parsed_cur = parse_price_value(str(el.get("content", "")))
            if value is None:
                continue
            out.append(
                PriceCandidate(
                    value=value,
                    currency=meta_currency or parsed_cur,
                    label="Preis",
                    source="meta",
                    locator={"strategy": "meta", "selector": selector, "attr": "content"},
                    raw=str(el.get("content", "")),
                    score=_SCORE_META,
                )
            )
    return out


def _extract_visible(soup: BeautifulSoup) -> list[PriceCandidate]:
    """Extrahiert sichtbare Preisangaben (Textknoten mit Währung, kurz)."""
    out: list[PriceCandidate] = []
    for node in soup.find_all(string=_PRICE_WITH_CURRENCY):
        text = node.strip()
        parent = node.parent
        if not text or len(text) > _MAX_VISIBLE_TEXT_LEN or not isinstance(parent, Tag):
            continue
        if parent.name in ("script", "style"):
            continue
        value, currency = parse_price_value(text)
        if value is None or value <= 0:
            continue
        score, context = _score_visible(parent, text)
        out.append(
            PriceCandidate(
                value=value,
                currency=currency,
                label=context or "Preis",
                source="visible",
                locator={
                    "strategy": "css",
                    "selector": _build_css_selector(soup, parent),
                    "value": value,
                },
                raw=text,
                context=context,
                score=score,
            )
        )
    return out


def _score_visible(el: Tag, raw: str) -> tuple[float, str | None]:
    """Bewertet einen sichtbaren Preis nach DOM-Kontext; (Score, Kontext-Hinweis).

    Rate im Preistext → Abschlag; Kaufbereich-Container → Boost; Streich-/UVP-Container →
    Abschlag. So landet der tatsächlich zu zahlende Preis oben, Nebenpreise darunter.
    """
    if _RATE_TEXT.search(raw):
        return _SCORE_VISIBLE_BASE - _SCORE_SECONDARY_PENALTY, "Monatliche Rate"
    # Text-Signal schlägt den Container: "UVP: 54,99 €" ist ein Streichpreis, auch wenn es in
    # einem Preis-Container steht.
    if _STRIKE_TEXT.search(raw):
        return _SCORE_VISIBLE_BASE - _SCORE_SECONDARY_PENALTY, "Streichpreis (UVP)"
    hint = _container_hint(el)
    if hint == "main":
        return _SCORE_VISIBLE_BASE + _SCORE_MAIN_CONTAINER_BOOST, "Preis im Kaufbereich"
    if hint == "strike":
        return _SCORE_VISIBLE_BASE - _SCORE_SECONDARY_PENALTY, "Streichpreis (UVP)"
    return _SCORE_VISIBLE_BASE, None


def _container_hint(el: Tag) -> str | None:
    """Sucht im Element und seinen nächsten Vorfahren nach Haupt-/Nebenpreis-Containern."""
    node: Tag | None = el
    for _ in range(_MAX_ANCESTOR_CLIMB + 1):
        if node is None:
            break
        tokens = _identifier_tokens(node)
        if any(any(k in t for k in _MAIN_PRICE_HINTS) for t in tokens):
            return "main"
        if any(any(k in t for k in _STRIKE_HINTS) for t in tokens):
            return "strike"
        node = node.parent if isinstance(node.parent, Tag) else None
    return None


def _identifier_tokens(el: Tag) -> list[str]:
    """id + Klassen eines Elements, klein geschrieben (für die Kontext-Heuristik)."""
    tokens = [str(el.get("id", "")).lower()]
    tokens += [str(c).lower() for c in (el.get("class") or [])]
    return [t for t in tokens if t]


def _base_css_selector(el: Tag) -> str:
    """Erzeugt einen möglichst stabilen Basis-Selektor für ein Element (ohne Eindeutigkeit)."""
    if el.get("id"):
        return f"#{el['id']}"
    if el.get("itemprop"):
        return f"{el.name}[itemprop='{el['itemprop']}']"
    classes = [c for c in (el.get("class") or []) if c]
    semantic = [c for c in classes if any(k in c.lower() for k in ("price", "amount", "cost"))]
    chosen = semantic or classes[:2]
    if chosen:
        return f"{el.name}." + ".".join(chosen)
    return el.name


def _anchor_selector(el: Tag) -> str | None:
    """Selektor für einen Vorfahren, der als Preis-Container taugt (id oder semantische Klasse)."""
    if el.get("id"):
        return f"#{el['id']}"
    classes = [c for c in (el.get("class") or []) if c]
    semantic = [c for c in classes if any(k in c.lower() for k in _SEMANTIC_ANCHOR_KEYS)]
    return f".{semantic[0]}" if semantic else None


def _build_css_selector(soup: BeautifulSoup, el: Tag) -> str:
    """Liefert einen Selektor, der ``el`` möglichst eindeutig trifft.

    Generische Klassen wie ``a-offscreen`` kommen auf Shop-Seiten dutzendfach vor; ein
    blanker Basis-Selektor träfe beim Monitoring den falschen Preis. Daher wird der
    Basis-Selektor an den nächsten id-/Preis-Vorfahren verankert, bis ``el`` eindeutig
    (oder zumindest der erste Treffer) ist.
    """
    base = _base_css_selector(el)
    matches = soup.select(base)
    if len(matches) == 1 and matches[0] is el:
        return base
    best = base
    for depth, ancestor in enumerate(el.parents):
        if depth >= _MAX_ANCESTOR_CLIMB:
            break
        if not isinstance(ancestor, Tag):
            continue
        anchor = _anchor_selector(ancestor)
        if not anchor:
            continue
        combined = f"{anchor} {base}"
        anchored = soup.select(combined)
        if not anchored or anchored[0] is not el:
            continue
        best = combined
        if len(anchored) == 1:
            return combined
    return best


def _dedupe_and_rank(candidates: list[PriceCandidate]) -> list[PriceCandidate]:
    """Dedupliziert nach Betrag (prominenteste Fundstelle gewinnt) und sortiert nach Prominenz.

    Ranking per Prominenz-Score (Hauptpreis-Wahrscheinlichkeit): strukturierte Daten und
    Kaufbereich-Preise oben, Streich-/Ratenpreise unten. Bei gleichem Score entscheidet die
    Häufigkeit: der echte Kaufpreis wird auf Shop-Seiten (Buy-Box, Zwischensumme, Sticky-Header)
    vielfach wiederholt, Nebenpreise meist nur einmal. So steht der wahrscheinliche Hauptpreis
    an erster Stelle (Default-Auswahl im Wizard).
    """
    counts = Counter(round(c.value, 2) for c in candidates)
    best: dict[float, PriceCandidate] = {}
    for cand in candidates:
        key = round(cand.value, 2)
        if key not in best or cand.score > best[key].score:
            best[key] = cand
    ordered = sorted(best.values(), key=lambda c: (-c.score, -counts[round(c.value, 2)], c.value))
    return ordered[:_MAX_CANDIDATES]


# ---------------------------------------------------------------------------
# Preis-Extraktion (beim Monitoring) per gespeichertem Locator
# ---------------------------------------------------------------------------
def extract_price(html: str, locator: dict) -> tuple[float | None, str | None]:
    """Wendet den gespeicherten Locator auf neues HTML an; (None, ...) wenn nicht auffindbar."""
    if not html or not locator:
        return None, None
    soup = BeautifulSoup(html, "html.parser")
    strategy = locator.get("strategy")
    if strategy == "jsonld":
        return _price_from_jsonld(soup, locator)
    if strategy == "meta":
        return _price_from_meta(soup, locator)
    if strategy == "css":
        return _price_from_css(soup, locator)
    return None, None


def _price_from_jsonld(soup: BeautifulSoup, locator: dict) -> tuple[float | None, str | None]:
    """Liest den Preis aus JSON-LD: gespeicherter Pfad zuerst, sonst erster Treffer."""
    scripts = soup.find_all("script", type="application/ld+json")
    index, path = locator.get("script_index"), locator.get("path", [])
    if isinstance(index, int) and 0 <= index < len(scripts):
        data = _load_json(scripts[index])
        value = _get_by_path(data, path)
        if value is not None:
            parsed, currency = parse_price_value(str(value))
            if parsed is not None:
                return parsed, currency
    # Fallback: erster Preis-Treffer über alle Blöcke (Struktur kann sich geändert haben).
    for script in scripts:
        hits: list = []
        _walk_jsonld(_load_json(script), [], hits)
        if hits:
            return hits[0][1], hits[0][2]
    return None, None


def _price_from_meta(soup: BeautifulSoup, locator: dict) -> tuple[float | None, str | None]:
    """Liest den Preis aus dem gespeicherten Meta-Selektor."""
    el = soup.select_one(locator.get("selector", ""))
    if not el:
        return None, None
    return parse_price_value(str(el.get(locator.get("attr", "content"), "")))


def _price_from_css(soup: BeautifulSoup, locator: dict) -> tuple[float | None, str | None]:
    """Liest den Preis aus dem gespeicherten CSS-Selektor (sichtbarer Text)."""
    try:
        matches = soup.select(locator.get("selector", ""))
    except Exception:  # noqa: BLE001 — ungültiger Selektor soll nicht crashen
        return None, None
    if not matches:
        return None, None
    el = _disambiguate_css_match(matches, locator.get("value"))
    return parse_price_value(el.get_text(strip=True))


def _disambiguate_css_match(matches: list[Tag], reference: object) -> Tag:
    """Wählt bei mehreren Treffern den, dessen Preis dem ursprünglich gewählten am nächsten ist."""
    if len(matches) == 1 or not isinstance(reference, int | float):
        return matches[0]

    def distance(el: Tag) -> float:
        value, _ = parse_price_value(el.get_text(strip=True))
        return abs(value - reference) if value is not None else float("inf")

    return min(matches, key=distance)


def _load_json(script: Tag) -> object:
    """Parst einen JSON-LD-Block; {} bei Fehler."""
    try:
        return json.loads(script.string or "")
    except (json.JSONDecodeError, TypeError):
        return {}


def _get_by_path(obj: object, path: list) -> object | None:
    """Folgt einem JSON-Pfad (Keys + Listen-Indizes); None bei Fehlschlag."""
    current = obj
    for step in path:
        try:
            current = current[step]  # type: ignore[index]
        except (KeyError, IndexError, TypeError):
            return None
    return current


# ---------------------------------------------------------------------------
# Optionale KI-Veredelung der Kandidaten-Labels
# ---------------------------------------------------------------------------
def refine_with_ai(candidates: list[PriceCandidate], title: str | None) -> list[PriceCandidate]:
    """Benennt Kandidaten nutzerfreundlich und markiert den Hauptpreis; Fallback heuristisch."""
    if not candidates:
        return candidates
    if not app_config.openai_api_key:
        _apply_heuristic_recommendation(candidates)
        return candidates
    try:
        _apply_ai_labels(candidates, title)
    except Exception as exc:  # noqa: BLE001 — KI ist optional, Fallback heuristisch
        logger.warning("KI-Benennung der Preis-Kandidaten fehlgeschlagen: %s", exc)
        _apply_heuristic_recommendation(candidates)
    return candidates


def _apply_ai_labels(candidates: list[PriceCandidate], title: str | None) -> None:
    """Ruft die KI auf und überträgt Labels + recommended-Flag auf die Kandidaten."""
    client = OpenAI(
        base_url=app_config.openai_base_url,
        api_key=app_config.openai_api_key,
        timeout=app_config.ai_request_timeout,
    )
    model = app_config.openai_cheap_model or app_config.openai_model
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": render_pricecandidates_system_prompt()},
            {
                "role": "user",
                "content": render_pricecandidates_user_prompt(
                    title, [c.model_dump() for c in candidates]
                ),
            },
        ],
        temperature=0.1,
        max_completion_tokens=500,
    )
    data = _parse_json_loose(response.choices[0].message.content)
    entries = data.get("candidates", []) if isinstance(data, dict) else []
    any_recommended = False
    for entry in entries:
        idx = entry.get("index")
        if not isinstance(idx, int) or not 0 <= idx < len(candidates):
            continue
        if entry.get("label"):
            candidates[idx].label = str(entry["label"]).strip()
        if entry.get("recommended") and not any_recommended:
            candidates[idx].recommended = True
            any_recommended = True
    if not any_recommended:
        _apply_heuristic_recommendation(candidates)


def _apply_heuristic_recommendation(candidates: list[PriceCandidate]) -> None:
    """Markiert den ersten (bestplatzierten) Kandidaten als empfohlen, falls keiner gesetzt ist."""
    if candidates and not any(c.recommended for c in candidates):
        candidates[0].recommended = True


def _parse_json_loose(content: str | None) -> object:
    """Parst JSON, auch wenn es in Markdown-Codefences verpackt ist."""
    if not content:
        return {}
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
