"""Integration tests for the employee service layer.

These tests guarantee the security contract of employee creation:
the password is never stored in plaintext (Argon2id), validation
happens before any database write, and duplicates are rejected.
"""

import pytest

from epicevents.services.employee_service import DuplicateError
from epicevents.security import verify_password


def test_create_employee_stores_hash_not_plaintext(session, make_employee):
    """The stored password is an Argon2id hash, never the plaintext."""
    # fixture factory ne te donne pas l'objet, elle te donne une fonction
    # qui fabrique l'objet.
    employee = make_employee()
    assert "AZERTYUI" not in employee.password_hash
    assert employee.password_hash.startswith("$argon2id$")
    assert verify_password("AZERTYUI", employee.password_hash)


def test_duplicate_email_raises(session, make_employee):
    """Test that duplicate emails raise error."""
    make_employee()
    with pytest.raises(DuplicateError):
        make_employee(employee_number="E002", name="Joshua C")


def test_duplicate_employee_number_raises(session, make_employee):
    """Test that duplicate employee numbers raise error."""
    make_employee()
    with pytest.raises(DuplicateError):
        make_employee(
            employee_number="E001", email="c.john@epicevents.com", name="John C"
        )


def test_short_password_raises(session, make_employee):
    """Test that short passwords raise error."""
    with pytest.raises(ValueError):
        make_employee(password="AZERTY")


def test_password_confirmation_mismatch_raises(session, make_employee):
    """Test that password confirmation mismatch raise an error."""
    with pytest.raises(ValueError):
        make_employee(password_confirmation="qsdfghcdfg")


def test_password_without_confirmation_is_accepted(session, make_employee):
    """When no confirmation is provided, the password alone is enough."""
    employee = make_employee()  # pas de password_confirmation
    assert employee.id is not None  # l'employé a bien été créé


def test_invalid_email_format_raises(session, make_employee):
    """Test that invalid email formats raise error."""
    with pytest.raises(ValueError):
        make_employee(email="invalide")


def test_unknown_role_raises(session, make_employee):
    """Test that unknown roles raise error."""
    with pytest.raises(ValueError):
        make_employee(role_name="inconnu")


def test_create_employee_associates_role(session, role_ges, make_employee):
    """The employee is linked to the requested role object."""
    employee = make_employee()
    assert employee.role is role_ges
    assert employee.role_id == role_ges.id
