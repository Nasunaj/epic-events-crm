"""Tests for client write services (permissions, scope, validation)."""

import pytest

from epicevents.exceptions import (
    DuplicateError,
    NotFoundError,
    NotOwnedError,
    PermissionDeniedError,
    ValidationError,
)
from epicevents.services.client_service import create_client, update_client


# --- create_client : rôle -------------
def test_commercial_creates_client(session, commercial):
    """A commercial can create a client, auto-assigned to them."""
    client = create_client(
        session,
        commercial,
        name="Nom CLient",
        email="client@startup.com",
        phone="0607080910",
        company_name="Startup SAS",
    )
    assert client.id is not None
    assert client.commercial.id == commercial.id


def test_support_cannot_create_client(session, support):
    """A support cannot create a client."""
    with pytest.raises(PermissionDeniedError):
        create_client(
            session,
            support,
            name="X",
            email="x@y.io",
            phone="0601020304",
            company_name="X Corp",
        )


def test_gestion_cannot_create_client(session, gestion):
    """Per the brief: gestion does NOT create clients."""
    with pytest.raises(PermissionDeniedError):
        create_client(
            session,
            gestion,
            name="X",
            email="x@y.io",
            phone="0601020304",
            company_name="X Corp",
        )


# --- create_client : validation -----------
def test_create_client_duplicate_email(session, commercial, client):
    """A client email already used is refused."""
    with pytest.raises(DuplicateError):
        create_client(
            session,
            commercial,
            name="X",
            email=client.email,
            phone="0601020304",
            company_name="X Corp",
        )


def test_create_client_invalid_email(session, commercial):
    """Invalid emails cannot be created."""
    with pytest.raises(ValidationError):
        create_client(
            session,
            commercial,
            name="X",
            email="emailno",
            phone="0601020304",
            company_name="X Corp",
        )


def test_create_client_empty_name(session, commercial):
    """Empty names cannot be created."""
    with pytest.raises(ValidationError):
        create_client(
            session,
            commercial,
            name="  ",
            email="ok@y.io",
            phone="0601020304",
            company_name="X Corp",
        )


# --- update_client : rôle + périmètre ------------
def test_commercial_updates_own_client(session, commercial, client):
    """The client's commercial can update their client."""
    updated = update_client(session, commercial, client.id, phone="+33 9 99 99 99 99")
    assert updated.phone == "+33 9 99 99 99 99"
    assert updated.last_update > updated.creation_date


def test_commercial_cannot_update_other_commercials_client(
    session, make_employee, client
):
    """The security test of this block: scope check."""
    commercial = make_employee(role_name="commercial", employee_number="E201")
    with pytest.raises(NotOwnedError):  # ⭐⭐
        update_client(session, commercial, client.id, name="blabla")


def test_support_cannot_update_client(session, support, client):
    """Support cannot update client."""
    with pytest.raises(PermissionDeniedError):
        update_client(session, support, client.id, name="X")


def test_update_unknown_client(session, commercial):
    """Unknown clients cannot update."""
    with pytest.raises(NotFoundError):
        update_client(session, commercial, 99999, name="X")


# --- update_client : whitelist + validation -----------
def test_update_rejects_forbidden_field(session, commercial, client):
    """commercial_id must not be writable (client never changes hands)."""
    with pytest.raises(ValidationError):
        update_client(session, commercial, client.id, commercial_id=99)


def test_update_no_fields(session, commercial, client):
    """No fields cannot be updated."""
    with pytest.raises(ValidationError):
        update_client(session, commercial, client.id)


def test_update_email_kept_by_client_is_allowed(session, commercial, client):
    """A client keeping their own email passes (exclude_id)."""
    updated = update_client(session, commercial, client.id, email=client.email)
    assert updated.email == client.email


def test_update_email_taken_by_other_client_rejected(
    session, commercial, client, make_client
):
    client2 = make_client()
    with pytest.raises(DuplicateError):
        update_client(session, commercial, client.id, email=client2.email)
