"""Event reading services: listings and display filters.

Read access is universal (all authenticated employees — see policies).
Filters required by the brief: events without support (for gestion),
events assigned to a specific support, events linked to the contracts
of a given commercial's clients.
"""

from sqlalchemy.orm import Session

from epicevents.auth import check_permission
from epicevents.exceptions import (
    PermissionDeniedError,
    NotFoundError,
    ValidationError,
    NotOwnedError,
    DuplicateError,
)
from epicevents.models import Contract, Event, Employee
from datetime import datetime

from epicevents.policies import EVENT_CREATORS, EVENT_UPDATERS, SUPPORT_ASSIGNERS
from epicevents.validation import require_non_empty, require_non_empty_if_present


def _base_query(session: Session):
    """Common ordered query shared by all event listings."""
    return session.query(Event).order_by(Event.event_date_start.desc())


def list_events(session: Session) -> list[Event]:
    """List every event, most recent first."""
    return _base_query(session).all()


def list_events_without_support(session: Session) -> list[Event]:
    """List events with no support assigned (gestion's workflow view)."""
    return _base_query(session).filter(Event.support_id.is_(None)).all()


def list_events_for_support(session: Session, employee: Employee) -> list[Event]:
    """List events assigned to this support employee."""
    return _base_query(session).filter_by(support_id=employee.id).all()


def list_events_for_commercial(session: Session, employee: Employee) -> list[Event]:
    """List events on contracts belonging to this commercial's clients."""
    return (
        _base_query(session)
        .join(Contract)
        .filter(Contract.commercial_id == employee.id)
        .all()
    )


# --- Writing -------------
def create_event(
    session: Session,
    employee: Employee,
    contract_id: int,
    name: str,
    event_date_start: datetime,
    event_date_end: datetime,
    location: str,
    attendees: int,
    note: str | None = None,
) -> Event:
    """Create an event on a SIGNED contract, by the contract's own commercial.
    Business rules (per the brief's workflow):
    - the contract must be signed (signature precedes the event);
    - one event per contract (unique constraint guarded here);
    - support is assigned later by gestion (event starts unassigned).
    """

    if not check_permission(employee, EVENT_CREATORS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas créer d'événement."
        )

    contract = session.get(Contract, contract_id)
    if contract is None:
        raise NotFoundError(f"Contrat introuvable : {contract_id}")

    if not contract.is_signed:
        raise ValidationError(
            "Le contrat n'étant pas signé, il est impossible de créer l'événement."
        )

    if contract.event is not None:
        raise DuplicateError("Ce contrat a déjà un événement associé.")

    if contract.commercial_id != employee.id:
        raise NotOwnedError(
            "Impossible de créer l'événement, le contrat associé n'est pas "
            "dans votre périmètre."
        )

    require_non_empty(location, "location")
    require_non_empty(name, "name")

    if event_date_start >= event_date_end:
        raise ValidationError(
            f"La date de fin de l’événement({event_date_end}) doit être "
            f"postérieure à sa date de début({event_date_start})."
        )

    # Booléen va être traduit par 1 donc à éviter aussi
    if not isinstance(attendees, int) or isinstance(attendees, bool) or attendees <= 0:
        raise ValidationError("Il faut au moins 1 participant à l'événement")

    event = Event(
        contract=contract,
        name=name,
        event_date_start=event_date_start,
        event_date_end=event_date_end,
        location=location,
        attendees=attendees,
        note=note,
    )
    session.add(event)
    session.commit()
    return event


UPDATABLE_FIELDS = {
    "name",
    "event_date_start",
    "event_date_end",
    "location",
    "attendees",
    "note",
}


def update_event(
    session: Session, employee: Employee, event_id: int, **fields_to_update
) -> Event:
    """Update an event. Support only, and only their own event.
    support_id and contract_id are not in the whitelist: assignment is
    gestion's job (see assign_support). Dates are validated together
    (final values)."""
    if not check_permission(employee, EVENT_UPDATERS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas modifier l'événement."
        )

    if not fields_to_update:
        raise ValidationError("Aucun champ à modifier.")

    event = session.get(Event, event_id)
    if event is None:
        raise NotFoundError(f"Evenement introuvable : {event_id}")

    if event.support_id != employee.id:
        raise NotOwnedError("Vous n'êtes pas assigné à cet événement.")

    for field in fields_to_update:
        if field not in UPDATABLE_FIELDS:
            raise ValidationError(f"Champ non modifiable : {field!r}")

    require_non_empty_if_present("name", fields_to_update)
    require_non_empty_if_present("location", fields_to_update)

    if "attendees" in fields_to_update:
        attendees = fields_to_update["attendees"]
        if (
            not isinstance(attendees, int)
            or isinstance(attendees, bool)
            or attendees <= 0
        ):
            raise ValidationError(
                "Le nombre de participants doit être un entier positif."
            )

    start = fields_to_update.get("event_date_start", event.event_date_start)
    end = fields_to_update.get("event_date_end", event.event_date_end)
    if end <= start:
        raise ValidationError(
            "La date de fin doit être postérieure à la date de début."
        )

    for field in UPDATABLE_FIELDS:
        if field in fields_to_update:
            setattr(event, field, fields_to_update[field])

    session.commit()
    return event


def assign_support(
    session: Session, employee: Employee, event_id: int, support_id: int
) -> Event:
    """Assign a support member to an event. Gestion only.
    The target must have the support role (per the brief). Reassigning
    replaces the current support.
    Raises PermissionDeniedError, NotFoundError or ValidationError."""

    if not check_permission(employee, SUPPORT_ASSIGNERS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas assigner de support."
        )
    event = session.get(Event, event_id)
    if event is None:
        raise NotFoundError(f"Evenement introuvable : {event_id}")
    support_target = session.get(Employee, support_id)
    if support_target is None:
        raise NotFoundError(f"Support introuvable : {support_id}")
    if support_target.role.name != "support":
        raise ValidationError(
            "Le collaborateur désigné n'est pas un membre du support."
        )
    event.support = support_target
    session.commit()
    return event
