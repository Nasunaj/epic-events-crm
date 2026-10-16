"""Tests for password hashing (security module)."""

from epicevents.security import hash_password, verify_password


def test_hash_starts_with_argon2id_marker():
    """Test Argon2id"""
    password_hash = hash_password("AZERTYUI")
    assert password_hash.startswith("$argon2id$")


def test_same_password_different_hashes():
    """Test 2 same password product different hashes"""
    password_hash1 = hash_password("AZERTYUI")
    password_hash2 = hash_password("AZERTYUI")
    assert password_hash1 != password_hash2


def test_verify_roundtrip():
    """Test verification if password already exists"""
    password_hash = hash_password("AZERTYUI")
    assert verify_password("AZERTYUI", password_hash) is True
    assert verify_password("blablazzz", password_hash) is False
    assert isinstance(verify_password("AZERTYUI", password_hash), bool)
