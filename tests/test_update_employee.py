"""Tests for employee updates (permission, whitelist, validation)."""

import pytest

from epicevents.exceptions import (
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from epicevents.services.employee_service import update_employee
from epicevents.security import verify_password


# --- Permission (rôle) -------------
def test_update_denied_for_non_gestion(session, commercial, make_employee):
    """Test no gestion can't update collaborators"""
    target = make_employee(role_name="commercial", employee_number="E901")
    with pytest.raises(PermissionDeniedError):
        update_employee(session, commercial, target.id, name="xxx")


def test_gestion_can_update_own_account(session, gestion, role_com, make_employee):
    """Test gestion can update owned account"""
    target = make_employee(role_name="commercial", employee_number="E901")
    update_employee(session, gestion, target.id, name="M Changement")
    assert target.name == "M Changement"


def test_update_changes_role(session, gestion, role_com, role_sup, make_employee):
    """Test update changes role"""
    target = make_employee(role_name="commercial", employee_number="E901")
    update_employee(session, gestion, target.id, role_name="support")
    assert target.role.name == "support"


# --- Cible ----------------
def test_update_unknown_employee_raises_not_found(session, gestion):
    with pytest.raises(NotFoundError):
        update_employee(session, gestion, 99999, name="X")


# --- Whitelist ------------
def test_forbidden_field_is_rejected(session, gestion, role_com, make_employee):
    """The heart of mass-assignment protection."""
    target = make_employee(role_name="commercial", employee_number="E901")
    with pytest.raises(ValidationError):
        update_employee(session, gestion, target.id, is_admin=True)


def test_role_id_injection_is_rejected(session, gestion, role_com, make_employee):
    """A caller cannot write the FK directly: role_name is the only way."""
    target = make_employee(role_name="commercial", employee_number="E901")
    with pytest.raises(ValidationError):
        update_employee(session, gestion, target.id, role_id=1)


# --- Validation avant écriture --------------
def test_no_fields_rejected(session, gestion, role_com, make_employee):
    """Test no fields"""
    target = make_employee(role_name="commercial", employee_number="E901")
    with pytest.raises(ValidationError):
        update_employee(session, gestion, target.id)


def test_short_password_rejected(session, gestion, role_com, make_employee):
    """Test short password"""
    target = make_employee(role_name="commercial", employee_number="E901")
    with pytest.raises(ValidationError):
        update_employee(session, gestion, target.id, password="azerty")


def test_email_taken_by_other_rejected(session, gestion, support, commercial):
    """Test duplicate against another employee is refused."""
    with pytest.raises(DuplicateError):
        update_employee(session, gestion, support.id, email=commercial.email)


def test_email_kept_by_target_is_allowed(session, gestion, commercial):
    """Test keeping your own email passes (exclude_id!)"""
    updated = update_employee(session, gestion, commercial.id, email=commercial.email)
    assert updated.email == commercial.email


def test_unknown_role_rejected(session, gestion, commercial):
    with pytest.raises(ValidationError):
        update_employee(session, gestion, commercial.id, role_name="direction")


# --- Ecriture -----------------
def test_update_password_is_hashed(session, gestion, commercial):
    """Never plaintext: hash verified via verify_password."""
    updated = update_employee(
        session, gestion, commercial.id, password="NouveauMotDePasse1"
    )
    assert updated.password_hash != "NouveauMotDePasse1"
    assert verify_password("NouveauMotDePasse1", updated.password_hash)
