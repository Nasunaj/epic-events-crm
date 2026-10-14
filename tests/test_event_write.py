"""Tests for event write services (workflow rules, scope, assignment)."""

from datetime import datetime, timezone, timedelta

import pytest

from epicevents.exceptions import (
    DuplicateError,
    NotFoundError,
    NotOwnedError,
    PermissionDeniedError,
    ValidationError,
)

from epicevents.services.event_service import (
    assign_support,
    create_event,
    update_event,
)

START = datetime(2026, 12, 1, 14, 0, tzinfo=timezone.utc)
END = datetime(2026, 12, 1, 22, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 12, 2, 10, 0, tzinfo=timezone.utc)


# --- create_event ---------
def test_commercial_creates_event_on_signed_own_contract(session, commercial, contract):
    """Test event on a signed contract, starts unassigned."""
    event = create_event(
        session,
        commercial,
        contract.id,
        name="Event 1",
        event_date_start=START,
        event_date_end=END,
        location="Paris",
        attendees=20,
    )
    assert event.name == "Event 1"
    assert event.note is None
    assert event.contract.id == contract.id
    assert event.support_id is None


def test_unsigned_contract_rejects_event(session, commercial, contract2):
    """Test no event before signature."""
    with pytest.raises(ValidationError):
        create_event(
            session,
            commercial,
            contract2.id,
            name="Event 1",
            event_date_start=START,
            event_date_end=END,
            location="Paris",
            attendees=20,
        )


def test_other_commercials_contract_rejects_event(
    session, make_employee, role_com, contract
):
    """Test only the contract's own commercial creates the event."""
    commercial2 = make_employee(
        role_name="commercial",
        employee_number="E201",
        email="blabl.employee@epicevents.com",
    )

    with pytest.raises(NotOwnedError):
        create_event(
            session,
            commercial2,
            contract.id,
            name="Event 2",
            event_date_start=START,
            event_date_end=END,
            location="Paris",
            attendees=20,
        )


def test_gestion_cannot_create_event(session, gestion, contract):
    """Test gestion can't create an event."""
    with pytest.raises(PermissionDeniedError):
        create_event(
            session,
            gestion,
            contract.id,
            name="Event 1",
            event_date_start=START,
            event_date_end=END,
            location="Paris",
            attendees=20,
        )


def test_one_event_per_contract(session, commercial, contract, event):
    """Test unique constraint guarded in the service (one contract = one event)."""
    with pytest.raises(DuplicateError):
        create_event(
            session,
            commercial,
            contract.id,
            name="Event 1",
            event_date_start=START,
            event_date_end=END,
            location="Paris",
            attendees=20,
        )


# create_event validation
def test_inverted_dates_rejected(session, commercial, contract):
    """Test event can't have start date < end date."""
    with pytest.raises(ValidationError):
        create_event(
            session,
            commercial,
            contract.id,
            name="Event 1",
            event_date_start=END,
            event_date_end=START,
            location="Paris",
            attendees=20,
        )


def test_zero_attendees_rejected(session, commercial, contract):
    """Test event can't have 0 attendees"""
    with pytest.raises(ValidationError):
        create_event(
            session,
            commercial,
            contract.id,
            name="Event 1",
            event_date_start=END,
            event_date_end=START,
            location="Paris",
            attendees=0,
        )


def test_boolean_attendees_rejected(session, commercial, contract):
    """Test True is an int in Python, the service must not fall for it."""
    with pytest.raises(ValidationError):
        create_event(
            session,
            commercial,
            contract.id,
            name="Event 1",
            event_date_start=END,
            event_date_end=START,
            location="Paris",
            attendees=True,
        )


# --- update_event -------------
def test_support_updates_own_event(session, support, event):
    """Test support is updated when event is owned."""
    updated = update_event(session, support, event.id, location="Salle 1")
    assert updated.location == "Salle 1"


def test_other_support_cannot_update_event(session, make_employee, role_sup, event):
    """test someone else's event is untouchable."""
    support2 = make_employee(role_name="support", employee_number="E201")
    with pytest.raises(NotOwnedError):
        update_event(session, support2, event.id, location="Salle 2")


def test_unassigned_event_rejects_update(session, support, event2):
    """Test no support = nobody responsible = nobody can update it."""
    with pytest.raises(NotOwnedError):
        update_event(session, support, event2.id, location="Partout")


def test_support_cannot_change_assignment_or_contract(
    session, support, event, make_employee, role_sup
):
    """Test the whitelist Is the boundary: support_id, contract_id unwritable."""
    support2 = make_employee(role_name="support", employee_number="E201")
    with pytest.raises(ValidationError):
        update_event(session, support, event.id, support_id=support2.id)
    with pytest.raises(ValidationError):
        update_event(session, support, event.id, contract_id=42)


def test_update_dates_validated_together(session, support, event):
    """Test writing only the end date below the existing start is refused."""
    with pytest.raises(ValidationError):
        update_event(
            session,
            support,
            event.id,
            event_date_end=event.event_date_start - timedelta(hours=1),
        )


# --- assign_support -------------
def test_gestion_assigns_support(session, gestion, event, support):
    """Test gestion can assign support."""
    updated = assign_support(session, gestion, event.id, support.id)
    assert updated.support.id == support.id


def test_commercial_cannot_assign(session, commercial, event, support):
    """Test commercial can not assign support."""
    with pytest.raises(PermissionDeniedError):
        assign_support(session, commercial, event.id, support.id)


def test_assign_non_support_role_rejected(session, gestion, event, commercial):
    """Test only a support department member can be designated."""
    with pytest.raises(ValidationError):  # ⭐
        assign_support(session, gestion, event.id, commercial.id)


def test_gestion_reassigns_support(
    session, gestion, event, support, make_employee, role_sup
):
    """Test reassignment replaces the current support."""
    support2 = make_employee(role_name="support", employee_number="E201")
    updated = assign_support(session, gestion, event.id, support2.id)
    assert updated.support.id == support2.id


def test_assign_unknown_support(session, gestion, event):
    """Test an unknown support can't be assigned."""
    with pytest.raises(NotFoundError):
        assign_support(session, gestion, event.id, 99999)
