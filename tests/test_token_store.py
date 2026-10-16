"""Tests for the token store."""

import os

from epicevents import token_store


def test_save_and_read_roundtrip(isolated_store):
    """A save token is read back automatically."""
    token_store.save_token("jeton-test")
    assert token_store.read_token() == "jeton-test"


def test_read_returns_none_when_no_token(isolated_store):
    """Before any login, read_token returns None (not an exception)."""
    assert token_store.read_token() is None


def test_clear_removes_the_file(isolated_store):
    """clear_token deletes the stored token file."""
    token_store.save_token("jeton-test")
    token_store.clear_token()
    assert token_store.read_token() is None
    assert not token_store.TOKEN_PATH.exists()


def test_clear_is_idempotent(isolated_store):
    """Calling clear_token twice or with no token does not crash."""
    token_store.clear_token()
    token_store.save_token("jeton-test")
    token_store.clear_token()
    token_store.clear_token()
    assert token_store.read_token() is None  # état final garanti
    assert not token_store.TOKEN_PATH.exists()


def test_saved_file_has_owner_only_permissions(isolated_store):
    """The token file is readable/writable by its owner only (0o600)."""
    token_store.save_token("jeton-test")
    #  Permissions 0o600, le test sécurité :
    # os.stat(chemin).st_mode renvoie le mode complet du fichier (avec les
    # bits de type, etc.) ;
    # & 0o777 : le ET bit à bit masque tout sauf les 9 bits de permissions
    # (propriétaire/groupe/autres). C'est comme un filtre qui isole la partie
    # qui nous intéresse ;
    # on compare le résultat à 0o600 : lecture+écriture pour le propriétaire
    # uniquement.
    # Le & binaire : si le mode vaut 0o100600 (fichier régulier + droits 600),
    # 0o100600 & 0o777 garde uniquement 0o600. Les bits au-delà de 777 sont
    # masqués à zéro. Technique standard pour tester des permissions Unix.
    mode = os.stat(token_store.TOKEN_PATH).st_mode & 0o777
    assert mode == 0o600
