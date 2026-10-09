"""Event reading services: listings and display filters.

Read access is universal (all authenticated employees — see policies).
Filters required by the brief: events without support (for gestion),
events assigned to a specific support, events linked to the contracts
of a given commercial's clients.
"""

from sqlalchemy.orm import Session

from epicevents.models import Contract, Event, Employee


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
