"""Persistent token storage on the user's machine.

The CLI is stateless: each command runs in a new process, so the JWT
issued at login must be stored on disk and re-read by every command.
This module is the CLI's session cookie"""

import os
from pathlib import Path

TOKEN_PATH = Path.home() / ".epicevents_token"


def save_token(token: str) -> None:
    """Write the token to disk with owner-only permissions."""
    # pathlib offre l'écriture directe. Pas besoin de open()/write()/
    # close() , tout (y compris la fermeture propre) est géré.
    TOKEN_PATH.write_text(token)
    # Le cœur sécuritaire. Sous Unix, chaque fichier a des droits en 3
    # chiffres : propriétaire / groupe / autres ; chaque chiffre = lecture(4) +
    # écriture(2) + exécution(1). 0o600 = 6 pour le propriétaire
    # (4+2 : lire et écrire), 0 pour le groupe, 0 pour les autres.
    # Personne d'autre que moi ne peut lire ce jeton => défense en
    # profondeur : même en cas d'accès au home, le fichier reste muet.
    os.chmod(TOKEN_PATH, 0o600)


def read_token() -> str | None:
    """Return the stored token, or None if no token file exists."""
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text()
    return None


def clear_token() -> None:
    """Remove the stored token (logout or expired session)."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
