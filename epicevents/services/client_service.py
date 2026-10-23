"""Client services: reading and writing.

Reading: access is universal (all authenticated employees — see
policies), filtered in the query (SQL), never after the fact.

Writing: creation is commercial-only with auto-assignment (the
caller becomes the client's commercial — no other commercial can
be chosen at the interface, by design); update is restricted to
the client's own commercial (scope check).
"""

from sqlalchemy.orm import Session
from epicevents.auth import check_permission
from epicevents.exceptions import (
    PermissionDeniedError,
    ValidationError,
    DuplicateError,
    NotFoundError,
    NotOwnedError,
)
from epicevents.models import Client, Employee
from epicevents.policies import CLIENT_CREATORS, CLIENT_UPDATERS
from epicevents.validation import (
    EMAIL_RE,
    require_non_empty,
    require_non_empty_if_present,
)
from datetime import datetime, timezone


def _validate_client_email(
    session: Session, email: str, exclude_id: int | None = None
) -> None:
    """Check that no OTHER client already uses this email."""
    query = session.query(Client).filter_by(email=email)
    if exclude_id is not None:
        query = query.filter(Client.id != exclude_id)
    if query.first():
        raise DuplicateError(f"Email client déjà utilisé : {email!r}")


# client_service.py
def list_clients(session):
    """Return all clients sorted by name (Python sort: name is encrypted at
    rest)."""
    clients = session.query(Client).all()
    return sorted(clients, key=lambda c: c.name)


def create_client(
    session: Session,
    employee: Employee,
    name: str,
    email: str,
    phone: str,
    company_name: str,
) -> Client:
    """Create a client. Commercial only, auto-assigned to them."""

    if not check_permission(employee, CLIENT_CREATORS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas créer un client."
        )

    require_non_empty(name, "name")

    if not email or not EMAIL_RE.match(email):
        raise ValidationError(f"Email invalide : {email!r}")

    _validate_client_email(session, email)

    require_non_empty(phone, "phone")

    require_non_empty(company_name, "company_name")

    now = datetime.now(timezone.utc)

    client = Client(
        name=name,
        email=email,
        phone=phone,
        company_name=company_name,
        creation_date=now,
        last_update=now,
        commercial=employee,
    )
    session.add(client)
    session.commit()
    return client


UPDATABLE_FIELDS = {"name", "email", "phone", "company_name"}


def update_client(
    session: Session, employee: Employee, client_id: int, **fields_to_update
) -> Client:
    """Update a client. Commercial only, and only their own client."""
    if not check_permission(employee, CLIENT_UPDATERS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas modifier un client."
        )

    if not fields_to_update:
        raise ValidationError("Aucun champ à modifier.")

    client = session.get(Client, client_id)
    if client is None:
        raise NotFoundError(f"Client introuvable : {client_id}")

    if client.commercial_id != employee.id:
        raise NotOwnedError("Ce client n'est pas dans votre périmètre.")

    for field in fields_to_update:
        if field not in UPDATABLE_FIELDS:
            raise ValidationError(f"Champ non modifiable : {field!r}")

    require_non_empty_if_present("name", fields_to_update)
    require_non_empty_if_present("company_name", fields_to_update)

    if "email" in fields_to_update:
        email = fields_to_update["email"]
        if not email or not EMAIL_RE.match(email):
            raise ValidationError(f"Email invalide : {email!r}")
        _validate_client_email(session, email, exclude_id=client.id)

    require_non_empty_if_present("phone", fields_to_update)

    for field in ("name", "email", "phone", "company_name"):
        if field in fields_to_update:
            setattr(client, field, fields_to_update[field])

    client.last_update = datetime.now(timezone.utc)

    session.commit()
    return client
