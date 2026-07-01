"""Plattform-Registry: Name → PlatformDefinition. Neue Quelle hier eintragen, sonst nichts.

Der restliche Code (ScraperService, künftig AIService/Frontend) kennt nur die abstrakten
Interfaces aus ``_base`` und holt konkrete Plattformen ausschließlich über ``get_platform``.
"""

from app.platforms._base import PlatformDefinition, PlatformScraper
from app.platforms.kleinanzeigen import Kleinanzeigen

DEFAULT_PLATFORM = "kleinanzeigen"

PLATFORM_REGISTRY: dict[str, PlatformDefinition] = {
    Kleinanzeigen.name: Kleinanzeigen(),
}


def get_platform(name: str) -> PlatformDefinition:
    """Plattform-Definition zum Namen; unbekannte Namen fallen auf die Standard-Plattform zurück."""
    return PLATFORM_REGISTRY.get(name, PLATFORM_REGISTRY[DEFAULT_PLATFORM])


def get_all_platform_names() -> list[str]:
    """Namen aller registrierten Plattformen."""
    return list(PLATFORM_REGISTRY)


__all__ = [
    "DEFAULT_PLATFORM",
    "PLATFORM_REGISTRY",
    "PlatformDefinition",
    "PlatformScraper",
    "get_all_platform_names",
    "get_platform",
]
