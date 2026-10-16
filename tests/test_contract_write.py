"""Tests for contract write services (permissions, scope, business rules)."""

import pytest

from epicevents.exceptions import (
    NotFoundError,
    NotOwnedError,
    PermissionDeniedError,
    ValidationError,
)

from epicevents.services.contract_service import create_contract, update_contract
from epicevents.validation import require_amount


# ---create_contract----------
def test_gestion_creates_contract_for_client(session, gestion, client):
    """Contract creation: gestion only, commercial inherited from client."""
    contract = create_contract(
        session, gestion, client.id, total_amount="10000", remaining_amount="10000"
    )
    assert contract.id is not None
    assert contract.client_id == client.id
    assert contract.commercial_id == client.commercial_id


def test_commercial_cannot_create_contract(session, commercial, client):
    """Per the brief: contracts are created by gestion, not commercial."""
    with pytest.raises(PermissionDeniedError):
        create_contract(
            session,
            commercial,
            client.id,
            total_amount="10000",
            remaining_amount="10000",
        )


def test_create_contract_unknown_client(session, gestion):
    with pytest.raises(NotFoundError):
        create_contract(
            session,
            gestion,
            99999,
            total_amount="10000",
            remaining_amount="10000",
        )


def test_create_remaining_exceeds_total_rejected(session, gestion, client):
    """Test remaining exceeds total rejected."""
    with pytest.raises(ValidationError):
        create_contract(
            session, gestion, client.id, total_amount="10000", remaining_amount="10001"
        )


def test_create_unsigned_with_partial_payment_rejected(session, gestion, client):
    """Test business rule: no money flows before signature."""
    with pytest.raises(ValidationError):
        create_contract(
            session,
            gestion,
            client.id,
            total_amount="10000",
            remaining_amount="7000",
            is_signed=False,
        )


def test_create_signed_with_partial_payment_allowed(session, gestion, client):
    """Test signature opens payment: signed + remaining < total is valid."""
    contract = create_contract(
        session,
        gestion,
        client.id,
        total_amount="10000",
        remaining_amount=7000,
        is_signed=True,
    )
    assert contract.is_signed is True
    assert contract.remaining_amount == 7000.00


def test_create_invalid_amount_rejected(session, gestion, client):
    """Test invalid amount rejected."""
    with pytest.raises(ValidationError):
        create_contract(
            session,
            gestion,
            client.id,
            total_amount="abc",
            remaining_amount="100",
        )


# --- update_contract ----------
def test_gestion_updates_any_contract(session, gestion, contract):
    """Test gestion updates any contract."""
    updated = update_contract(session, gestion, contract.id, is_signed=True)
    assert updated.is_signed is True


def test_commercial_updates_own_clients_contract(session, commercial, contract):
    """Test commercial updates own clients contract."""
    updated = update_contract(session, commercial, contract.id, remaining_amount="100")
    assert updated.is_signed is True
    assert contract.remaining_amount == 100


def test_commercial_cannot_update_other_contract(
    session, make_employee, contract, role_com
):
    """Test the security test: scope check on someone else's contract."""
    commercial = make_employee(role_name="commercial")
    with pytest.raises(NotOwnedError):
        update_contract(session, commercial, contract.id, is_signed=True)


def test_commercial_cannot_move_contract_to_another_client(
    session, commercial, contract
):
    """Test the scope-escalation guard: client_id is gestion-only."""
    with pytest.raises(PermissionDeniedError):
        update_contract(session, commercial, contract.id, client_id=42)


def test_update_total_below_existing_remaining_rejected(session, gestion, contract):
    """Test lowering total under the existing remaining is incoherent."""
    with pytest.raises(ValidationError):
        update_contract(session, gestion, contract.id, total_amount="10")


def test_update_unsigned_with_partial_payment_rejected(session, gestion, contract):
    """Test the signature rule holds on the update path too."""
    # contract: signed, remaining 5000 => on désigne ET on ouvre le paiement,
    # puis on essaye de mettre à jour is_signed False impossible car déjà
    # paiement
    with pytest.raises(ValidationError):
        update_contract(session, gestion, contract.id, is_signed=False)


def test_gestion_reassigns_client_commercial_follows(
    session, gestion, contract, make_employee, make_client, role_com
):
    """Test relational update: the contract's commercial follows the client."""
    com_a = make_employee(
        employee_number="E101",
        email="a.a@epicevents.com",
        name="Al A",
        role_name="commercial",
    )
    client_a = make_client(commercial=com_a, email="ca@client.com", name="Client A")
    print(contract.commercial.name)
    print(contract.client.name)

    updated = update_contract(session, gestion, contract.id, client_id=client_a.id)
    assert updated.client.id == client_a.id
    assert updated.commercial.id == client_a.commercial.id
    print(contract.commercial.name)
    print(contract.client.name)


def test_amount_infinity_rejected():
    with pytest.raises(ValidationError):
        require_amount("inf", "total")
