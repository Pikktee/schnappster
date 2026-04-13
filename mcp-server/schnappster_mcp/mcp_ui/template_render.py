"""Jinja2-Rendering für eingebettete MCP-App-HTML (ext-apps)."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateNotFound

# Gleiche CDN-Zeile wie im offiziellen ext-apps qr-server-Beispiel (stabile 0.4.x).
EXT_APPS_APP_WITH_DEPS = (
    "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps"
)

_TEMPLATES_ROOT = files("schnappster_mcp.mcp_ui").joinpath("templates")


class _PackageLoader(BaseLoader):
    """Lädt Templates aus dem ``mcp_ui/templates/``-Paketverzeichnis (für Includes)."""

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str | None, None]:
        resource = _TEMPLATES_ROOT.joinpath(template)
        try:
            source = resource.read_text(encoding="utf-8")
        except (FileNotFoundError, TypeError) as exc:
            raise TemplateNotFound(template) from exc
        return source, template, None


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    """Singleton-Jinja2-Environment mit Package-Loader (cached)."""
    return Environment(
        loader=_PackageLoader(),
        undefined=StrictUndefined,
        autoescape=False,
    )


def render_mcp_app_html(
    template_name: str,
    *,
    ext_apps_import_url: str | None = None,
) -> str:
    """Lädt ``templates/<template_name>`` und rendert mit Jinja2.

    Autoescape ist aus: fast nur ``<script>``-Inhalt; die CDN-URL ist vertrauenswürdig.
    """
    url = ext_apps_import_url or EXT_APPS_APP_WITH_DEPS
    tpl = _jinja_env().get_template(template_name)
    return tpl.render(ext_apps_import_url=url)
