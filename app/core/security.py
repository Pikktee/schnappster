"""Passwort-Hashing (bcrypt) und Passwort-Policy."""

import re

import bcrypt

# bcrypt verarbeitet maximal 72 Bytes; laengere Passwoerter werden konsistent gekuerzt.
_BCRYPT_MAX_BYTES = 72


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Erzeugt einen bcrypt-Hash fuer das Passwort."""
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Prueft ein Passwort gegen den gespeicherten bcrypt-Hash."""
    try:
        return bcrypt.checkpw(_encode(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def validate_password_strength(password: str) -> None:
    """Prueft Mindestlaenge, Gross-/Kleinbuchstaben und Sonderzeichen.

    Wirft ``ValueError`` mit einer deutschen Meldung (Routen wandeln das in HTTP 422).
    """
    errors: list[str] = []
    if len(password) < 8:
        errors.append("mindestens 8 Zeichen")
    if not re.search(r"[A-Z]", password):
        errors.append("einen Grossbuchstaben")
    if not re.search(r"[a-z]", password):
        errors.append("einen Kleinbuchstaben")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("ein Sonderzeichen")
    if errors:
        raise ValueError(f"Passwort benoetigt: {', '.join(errors)}.")
