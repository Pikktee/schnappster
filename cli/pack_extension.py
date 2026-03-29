"""Pack the Chrome extension into a store-ready ZIP archive.

Usage:
    uv run release-chrome-extension
    uv run release-chrome-extension minor
    uv run release-chrome-extension --output-dir extensions/dist
    uv run release-chrome-extension --output extensions/dist/custom.zip
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.core import get_app_root, setup_logging

DEFAULT_ZIP_BASE = "schnappster-chrome-extension"
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Packt die Chrome-Extension als ZIP-Datei.")
    parser.add_argument(
        "part",
        nargs="?",
        choices=("patch", "minor", "major"),
        default="patch",
        help="Welche Versionsstelle gebumpt wird (Standard: patch).",
    )
    parser.add_argument(
        "--output-dir",
        "-d",
        default="extensions/dist",
        help=(
            "Ausgabeordner für das ZIP (relativ zum Projekt-Root oder absolut). "
            "Standard: extensions/dist"
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        help=(
            "Optionaler exakter Pfad zur ZIP-Datei (überschreibt --output-dir). "
            "Relativ zum Projekt-Root oder absolut."
        ),
    )
    return parser


def _resolve_path(root: Path, path_arg: str) -> Path:
    path = Path(path_arg)
    if path.is_absolute():
        return path
    return root / path


def _bump_version(version: str, part: str) -> str:
    match = VERSION_RE.match(version)
    if not match:
        raise SystemExit(f"❌ Ungültige Manifest-Version '{version}'. Erwartet: X.Y.Z")
    major, minor, patch = (int(value) for value in match.groups())
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def _load_manifest(manifest_path: Path) -> dict:
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"❌ manifest.json konnte nicht gelesen werden: {exc}") from exc


def _resolve_output_path(
    root: Path,
    output_arg: str | None,
    output_dir_arg: str,
    version: str,
) -> Path:
    if output_arg:
        output_path = _resolve_path(root, output_arg)
        if output_path.suffix.lower() != ".zip":
            output_path = output_path.with_suffix(".zip")
        return output_path
    output_dir = _resolve_path(root, output_dir_arg)
    file_name = f"{DEFAULT_ZIP_BASE}-v{version}.zip"
    return output_dir / file_name


def _collect_files(extension_dir: Path) -> list[Path]:
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
    return files


def _relative_to_root(path: Path, root: Path) -> str:
    rel = path.relative_to(root) if path.is_relative_to(root) else path
    return str(rel)


def main() -> None:
    setup_logging()
    args = _build_parser().parse_args()

    root = get_app_root()
    extension_dir = root / "extensions" / "chrome"
    manifest_path = extension_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("❌ manifest.json nicht gefunden in extensions/chrome/")

    manifest = _load_manifest(manifest_path)
    current_version = str(manifest.get("version", "")).strip()
    new_version = _bump_version(current_version, args.part)
    manifest["version"] = new_version
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2)
    manifest_path.write_text(f"{manifest_json}\n", encoding="utf-8")

    output_path = _resolve_output_path(root, args.output, args.output_dir, new_version)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = _collect_files(extension_dir)
    if not files:
        raise SystemExit("❌ Keine Dateien zum Packen gefunden.")

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in sorted(files):
            arcname = file_path.relative_to(extension_dir)
            zip_file.write(file_path, arcname.as_posix())

    rel_manifest = _relative_to_root(manifest_path, root)
    rel_output = _relative_to_root(output_path, root)
    print(f"✅ Version erhöht: {current_version} -> {new_version} ({args.part})")
    print(f"✅ Manifest aktualisiert: {rel_manifest}")
    print(f"✅ Extension-ZIP erstellt: {rel_output}")
    print(f"   Dateien im Archiv: {len(files)}")
