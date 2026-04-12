"""Tests für Jinja2-geladene MCP-App-Templates."""

from schnappster_mcp.mcp_ui_jinja import EXT_APPS_APP_WITH_DEPS, render_mcp_app_html


def test_render_injects_ext_apps_cdn_url() -> None:
    html = render_mcp_app_html("bargain_detail.html.j2")
    assert EXT_APPS_APP_WITH_DEPS in html
    assert "unpkg.com" in html
    assert "__EXT_APPS_IMPORT__" not in html
    assert "{{ ext_apps_import_url }}" not in html


def test_render_accepts_custom_cdn_url() -> None:
    custom = "https://example.invalid/ext-apps.js"
    html = render_mcp_app_html("bargain_detail.html.j2", ext_apps_import_url=custom)
    assert custom in html
    assert EXT_APPS_APP_WITH_DEPS not in html
