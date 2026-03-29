"""Pack the Chrome extension into a store-ready ZIP archive.

Usage:
    uv run pack-extension
    uv run pack-extension --output extensions/chrome/my-extension.zip
"""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.core import get_app_root, setup_logging

DEFAULT_ZIP_NAME = "schnappster-chrome-extension.zip"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Packt die Chrome-Extension als ZIP-Datei.")
    parser.add_argument(
        "--output",
        "-o",
        help=(
            "Pfad zur ZIP-Datei (relativ zum Projekt-Root oder absolut). "
            f"Standard: extensions/chrome/{DEFAULT_ZIP_NAME}"
        ),
    )
    return parser


def _resolve_output_path(root: Path, output_arg: str | None) -> Path:
    if not output_arg:
        return root / "extensions" / "chrome" / DEFAULT_ZIP_NAME
    output_path = Path(output_arg)
    if output_path.is_absolute():
        return output_path
    return root / output_path


def main() -> None:
    setup_logging()
    args = _build_parser().parse_args()

    root = get_app_root()
    extension_dir = root / "extensions" / "chrome"
    manifest_path = extension_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("❌ manifest.json nicht gefunden in extensions/chrome/")

    output_path = _resolve_output_path(root, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    for path in extension_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".zip":
            # Bereits gebaute Archive niemals rekursiv wieder einpacken.
            continue
        if path.name == ".DS_Store":
            continue
        files.append(path)

    if not files:
        raise SystemExit("❌ Keine Dateien zum Packen gefunden.")

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in sorted(files):
            arcname = file_path.relative_to(extension_dir)
            zip_file.write(file_path, arcname.as_posix())

    rel_output = output_path.relative_to(root) if output_path.is_relative_to(root) else output_path
    print(f"✅ Extension-ZIP erstellt: {rel_output}")
    print(f"   Dateien im Archiv: {len(files)}")
