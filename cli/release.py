"""
Release-Script für Schnappster.
Verwendung: uv run release [major|minor|patch]
Default: patch (z.B. v1.0.0 → v1.0.1)
"""

import re
import subprocess
import sys
from pathlib import Path


def run(cmd: str, capture: bool = False) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    if result.returncode != 0:
        print(f"❌ Fehler bei: {cmd}")
        if capture:
            print(result.stderr)
        sys.exit(1)
    return result.stdout.strip() if capture else ""


def get_version_from_pyproject() -> tuple[int, int, int]:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return (0, 0, 0)
    content = pyproject.read_text()
    m = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content, re.MULTILINE)
    if not m:
        return (0, 0, 0)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def get_current_version() -> tuple[int, int, int]:
    """Nimmt das neueste Git-Tag, fällt auf pyproject.toml zurück wenn keins existiert."""
    tags = run("git tag --list 'v*' --sort=-version:refname", capture=True)
    if tags:
        latest = tags.splitlines()[0]
        m = re.match(r"v(\d+)\.(\d+)\.(\d+)", latest)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
    # Kein Tag vorhanden – aus pyproject.toml lesen
    version = get_version_from_pyproject()
    if any(version):
        print(
            "ℹ️  Kein Git-Tag gefunden, nutze Version aus pyproject.toml: "
            f"{version[0]}.{version[1]}.{version[2]}"
        )
    return version


def bump(major: int, minor: int, patch: int, part: str) -> tuple[int, int, int]:
    if part == "major":
        return major + 1, 0, 0
    elif part == "minor":
        return major, minor + 1, 0
    else:
        return major, minor, patch + 1


def update_pyproject_version(new_version: str) -> None:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("⚠️  pyproject.toml nicht gefunden, überspringe Version-Update.")
        return
    content = pyproject.read_text()
    updated = re.sub(
        r'^(version\s*=\s*")[^"]*(")',
        rf'\g<1>{new_version}\g<2>',
        content,
        flags=re.MULTILINE,
    )
    if updated == content:
        print("⚠️  Kein 'version = ...' in pyproject.toml gefunden, überspringe.")
        return
    pyproject.write_text(updated)


def main() -> None:
    part = sys.argv[1] if len(sys.argv) > 1 else "patch"
    if part not in ("major", "minor", "patch"):
        print("Verwendung: uv run release [major|minor|patch]")
        sys.exit(1)

    # Sicherstellen dass working tree sauber ist
    dirty = run("git status --porcelain", capture=True)
    if dirty:
        print("❌ Working tree ist nicht sauber. Bitte erst committen:")
        print(dirty)
        sys.exit(1)

    # Aktuellen Branch prüfen
    branch = run("git rev-parse --abbrev-ref HEAD", capture=True)
    if branch != "main":
        print(f"⚠️  Du bist auf Branch '{branch}', nicht 'main'. Fortfahren? [y/N] ", end="")
        if input().strip().lower() != "y":
            sys.exit(0)

    current = get_current_version()
    new = bump(*current, part)
    old_version = f"{current[0]}.{current[1]}.{current[2]}"
    new_version = f"{new[0]}.{new[1]}.{new[2]}"
    old_tag = f"v{old_version}" if any(current) else "(kein Tag)"
    new_tag = f"v{new_version}"

    print(f"\n🏷️  {old_tag} → {new_tag}")
    print(f"   Typ: {part}")
    print("\nVersion bumpen, committen und pushen? [y/N] ", end="")
    if input().strip().lower() != "y":
        print("Abgebrochen.")
        sys.exit(0)

    # Versionsdateien aktualisieren
    update_pyproject_version(new_version)
    run("uv lock")

    # Version-Bump committen
    run("git add pyproject.toml uv.lock")
    run(f'git commit -m "chore: bump version to {new_tag}"')
    run("git push origin main")

    # Tag erstellen und pushen
    run(f'git tag -a {new_tag} -m "Release {new_tag}"')
    run(f"git push origin {new_tag}")

    print(f"\n✅ {new_tag} gepusht.")


if __name__ == "__main__":
    main()