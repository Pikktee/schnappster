"""Build documentation: pdoc (Backend-Code), Architektur, Frontend-Übersicht.

Usage:
    uv run docs           # build docs into docs/build
    uv run docs --open    # build and open in browser
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from app.core import get_app_root, setup_logging

# Relative path from build root to _static (same for all our pages in build/)
STATIC_PREFIX = "_static"


def _nav_html(active: str | None) -> str:
    """Build navigation HTML for doc pages (Start, Backend, Frontend, Architektur)."""
    items = [
        ("index.html", "Start", None),
        ("app.html", "Backend (Referenz)", "code"),
        ("frontend.html", "Frontend", "frontend"),
        ("architecture.html", "Architektur", "arch"),
    ]
    parts = []
    for href, label, key in items:
        cls = ' class="is-active"' if key == active else ""
        parts.append(f'<a href="{href}"{cls}>{label}</a>')
    logo_src = f"{STATIC_PREFIX}/logo.svg"
    return (
        '<nav class="doc-nav" aria-label="Dokumentation">'
        '<div class="doc-nav-inner">'
        f'<a href="index.html" class="doc-nav-home" aria-label="Schnappster">'
        f'<img src="{logo_src}" alt="" class="doc-nav-logo" width="140" height="140">'
        "</a>"
        '<span class="doc-nav-sep">·</span>'
        + " ".join(parts)
        + "</div></nav>"
    )


def _doc_page(
    title: str,
    body: str,
    *,
    active: str | None = None,
    back_link: bool = False,
) -> str:
    """Build full HTML page with shared layout and doc.css."""
    back = ''
    if back_link:
        back = '<a href="index.html" class="doc-back">← Zur Übersicht</a>'
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} – Schnappster</title>
  <link rel="stylesheet" href="{STATIC_PREFIX}/doc.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
        rel="stylesheet">
</head>
<body>
  {_nav_html(active)}
  <main class="doc-main">
    {back}
    {body}
  </main>
</body>
</html>
"""


def _markdown_to_html(
    raw: str,
    image_prefix: str = "",
    code_to_img_pattern: str = r"<code>([a-zA-Z0-9_.-]+\.(?:png|svg))</code>",
    img_prefix_replace: str = r'<figure><img src="\1" alt="\1" style="max-width:100%;"/></figure>',
) -> str:
    """Convert Markdown to HTML; optional image prefix and code-to-img replacement."""
    try:
        import markdown
    except ImportError:
        return f"<pre>{raw}</pre>"
    # Bildpfade in ![alt](path) anpassen
    if image_prefix:
        raw = re.sub(
            r"(!\[[^\]]*\]\()([^/)]+\.(?:png|svg|jpg))",
            rf"\1{image_prefix}\2",
            raw,
        )
    html = markdown.markdown(raw, extensions=["extra", "nl2br"])
    if code_to_img_pattern and img_prefix_replace:
        html = re.sub(code_to_img_pattern, img_prefix_replace, html)
    return html


def _inject_pdoc_back_link(html_path: Path, build_dir: Path) -> None:
    """Inject back-link and doc.css into a pdoc-generated HTML file."""
    try:
        text = html_path.read_text(encoding="utf-8")
    except OSError:
        return
    rel = html_path.relative_to(build_dir)
    depth = len(rel.parts) - 1
    prefix = "../" * depth if depth else "./"
    index_url = f"{prefix}index.html"
    css_url = f"{prefix}{STATIC_PREFIX}/doc.css"
    back_div = (
        f'<div class="doc-pdoc-back">'
        f'<a href="{index_url}">← Zur Dokumentations-Übersicht</a></div>'
    )
    # CSS vor </head> einfügen (nur wenn noch nicht vorhanden)
    if "doc.css" not in text:
        text = text.replace("</head>", f'  <link rel="stylesheet" href="{css_url}">\n</head>', 1)
    # Back-Div nach <body> oder <body ...> einfügen (nur wenn noch nicht vorhanden)
    if "doc-pdoc-back" not in text:
        text = re.sub(r"<body([^>]*)>", rf"<body\1>\n  {back_div}", text, count=1)
    html_path.write_text(text, encoding="utf-8")


def main() -> None:
    """Build docs (pdoc, architecture, frontend) into docs/build; optionally open in browser."""
    setup_logging()
    args = set(sys.argv[1:])
    open_browser = "--open" in args or "-O" in args

    root = get_app_root()
    docs_dir = root / "docs"
    build_dir = docs_dir / "build"
    arch_dir = docs_dir / "architecture"
    frontend_dir = docs_dir / "frontend"
    static_dir = docs_dir / "_static"
    pdoc_templates = docs_dir / "templates" / "pdoc"

    build_dir.mkdir(parents=True, exist_ok=True)

    # 1. pdoc: Backend-Code-Referenz
    print("\n" + "=" * 60)
    print("📚  Code-Referenz (pdoc)")
    print("=" * 60 + "\n")
    pdoc_cmd = [sys.executable, "-m", "pdoc", "app", "-o", str(build_dir)]
    if pdoc_templates.exists():
        pdoc_cmd.extend(["-t", str(pdoc_templates)])
    result = subprocess.run(pdoc_cmd, cwd=str(root), check=False)
    if result.returncode != 0:
        print("pdoc failed. Install dev deps: uv sync")
        sys.exit(result.returncode)

    # 2. Gemeinsame Ressourcen
    static_out = build_dir / STATIC_PREFIX
    static_out.mkdir(parents=True, exist_ok=True)
    if static_dir.exists():
        for f in static_dir.iterdir():
            if f.is_file():
                shutil.copy2(f, static_out / f.name)
        print("Copied _static into build")
    # Logo aus Frontend für Header
    web_logo = root / "web" / "public" / "logo.svg"
    if web_logo.exists():
        shutil.copy2(web_logo, static_out / "logo.svg")
        print("Copied logo.svg from web/public into build")

    # 3. Architektur
    if arch_dir.exists():
        arch_out = build_dir / "architecture"
        arch_out.mkdir(parents=True, exist_ok=True)
        for ext in ("*.png", "*.svg"):
            for f in arch_dir.glob(ext):
                shutil.copy2(f, arch_out / f.name)
        arch_md = arch_dir / "ARCHITECTURE.md"
        if arch_md.exists():
            raw = arch_md.read_text(encoding="utf-8")
            html_body = _markdown_to_html(
                raw,
                image_prefix="architecture/",
                img_prefix_replace=(
                    r'<figure><img src="architecture/\1" alt="\1" style="max-width:100%;"/>'
                    r'</figure>'
                ),
            )
            page = _doc_page(
                "Architektur",
                html_body,
                active="arch",
                back_link=True,
            )
            (build_dir / "architecture.html").write_text(page, encoding="utf-8")
            print("Generated architecture.html")

    # 4. Frontend-Übersicht
    frontend_md = frontend_dir / "FRONTEND.md" if frontend_dir.exists() else None
    if frontend_md and frontend_md.exists():
        raw = frontend_md.read_text(encoding="utf-8")
        html_body = _markdown_to_html(raw, image_prefix="")
        page = _doc_page(
            "Frontend",
            html_body,
            active="frontend",
            back_link=True,
        )
        (build_dir / "frontend.html").write_text(page, encoding="utf-8")
        print("Generated frontend.html")

    # 5. Startseite (Übersicht mit Kacheln): 1. Backend, 2. Frontend, 3. Architektur
    cards = []
    cards.append(
        '<a href="app.html" class="doc-card">'
        "<h2>Backend (Referenz)</h2>"
        "<p>Python-Module, Klassen und Funktionen – automatisch aus Docstrings (pdoc).</p></a>"
    )
    if (build_dir / "frontend.html").exists():
        cards.append(
            '<a href="frontend.html" class="doc-card">'
            "<h2>Frontend</h2>"
            "<p>Routen, Struktur und Komponenten der Next.js-App.</p></a>"
        )
    if (build_dir / "architecture.html").exists():
        cards.append(
            '<a href="architecture.html" class="doc-card">'
            "<h2>Architektur</h2>"
            "<p>Systemüberblick, Backend-Schichten, Produktion vs. Development.</p></a>"
        )
    body = (
        "<h1>Dokumentation</h1>"
        '<p class="doc-intro">Übersicht über Backend-Code, Frontend und Architektur.</p>'
        '<div class="doc-cards">' + "".join(cards) + "</div>"
    )
    index_html = _doc_page("Dokumentation", body, active=None)
    (build_dir / "index.html").write_text(index_html, encoding="utf-8")
    print("Updated index.html")

    # 6. Back-Link + doc.css in alle pdoc-Seiten injizieren
    skip = {"index.html", "architecture.html", "frontend.html"}
    for html_path in build_dir.rglob("*.html"):
        if html_path.name in skip:
            continue
        _inject_pdoc_back_link(html_path, build_dir)
    print("Injected back-links into Code-Referenz pages")

    print("\n" + "=" * 60)
    print("✅  DOCUMENTATION BUILT: docs/build/")
    print("=" * 60 + "\n")

    if open_browser:
        index_path = build_dir / "index.html"
        if index_path.exists():
            webbrowser.open(index_path.as_uri())
        else:
            webbrowser.open(build_dir.as_uri())
