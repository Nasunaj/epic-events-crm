"""Integration tests for ORM models and relations."""

from datetime import datetime
import pytest
from sqlalchemy.exc import IntegrityError
from epicevents.models import Employee, Event


def test_client_belongs_to_its_commercial(commercial, client):
    """Test client belongs to commercial."""
    assert client.commercial_id == commercial.id
    assert client.commercial is commercial
    assert client in commercial.clients


def test_employee_without_role_cant_insert(session):
    """ "Test employee cannot be inserted without role."""
    josh = Employee(
        employee_number="E001",
        name="Josh C",
        email="c.josh@epicevents.com",
        password_hash="hache1",
    )
    session.add_all([josh])
    with pytest.raises(IntegrityError):
        # # c'est ici que le SQL part et que la contrainte se déclenche
        session.commit()
    session.rollback()  # on nettoie la transaction échouée


def test_2_employees_with_same_email(session):
    """Test two employees cannot have the same email."""
    josh = Employee(
        employee_number="E001",
        name="Josh C",
        email="c.josh@epicevents.com",
        password_hash="hache1",
    )
    jo = Employee(
        employee_number="E002",
        name="Jo C",
        email="c.josh@epicevents.com",
        password_hash="hache1",
    )
    session.add_all([jo, josh])
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_contract_access_its_client_and_its_commercial(client, commercial, contract):
    """A contract accesses its client via `contract.client` and its sales
    representative via `contract.commercial`."""
    assert contract.client == client
    assert contract.commercial == commercial


def test_2_events_cannot_have_same_contract(session, contract, support):
    """Test two events cannot have the same contract."""
    event = Event(
        contract=contract,
        name="xxxx Party",
        event_date_start=datetime(2026, 10, 1, 13),
        event_date_end=datetime(2026, 10, 2, 2),
        location="1 ..., Paris",
        attendees=75,
        note="DJ",
        support=support,
    )

    event2 = Event(
        contract=contract,
        name="xxxx Party2",
        event_date_start=datetime(2026, 10, 2, 10),
        event_date_end=datetime(2026, 10, 2, 14),
        location="1 ..., Quimper",
        attendees=100,
        note="DJ",
        support=support,
    )

    session.add_all([event, event2])
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_event_without_support_is_allowed(event2):
    """Test event can be created without support ID."""
    assert event2.support is None
    assert event2.support_id is None


def test_contract_event_returns_single_object(contract, event):
    """Test contract event returns single object."""
    assert contract.event is event
    assert not isinstance(contract.event, list)
    assert contract.event.name == "xxxx Party"


def test_support_sees_their_events(event, support):
    """A support employee reaches the events assigned to them."""
    assert event in support.events


# Test __repr__


def test__repr__(session, role_com, client, contract, event, commercial):
    """Test __repr__ method."""
    assert "commercial" in role_com.__repr__()
    assert "Josh C" in commercial.__repr__()
    assert "Kevin Casey" in client.__repr__()
    assert "1000" in contract.__repr__()
    assert "xxxx Party" in event.__repr__()
