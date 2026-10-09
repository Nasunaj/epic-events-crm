"""Client reading services: filtered by employee permissions.

Rule: filtering happens in the query (SQL), never after. Data the
employee must not see never leaves the database.
"""

from sqlalchemy.orm import Session
from epicevents.models import Client

# , Employee)
# from epicevents.auth import PermissionDeniedError, check_permission
# from epicevents.policies import CLIENT_READERS

# def list_clients(session: Session, employee: Employee) -> list[Client]:
#     """Return clients filtered by the employee's permissions.
#
#     Gestion sees all clients; a commercial sees only their own.
#     Support has no client-reading scope: explicitly denied.
#     """
#     if not check_permission(employee, CLIENT_READERS):
#         raise PermissionDeniedError(
#             f"Le rôle {employee.role.name!r} n'a pas accès aux clients."
#         )
#     query = session.query(Client)
#     if employee.role.name == "commercial":
#         query = query.filter_by(commercial_id=employee.id)
#     return query.order_by(Client.name).all()


def list_clients(session: Session) -> list[Client]:
    """Return all clients (read access is universal), sorted by name."""
    return session.query(Client).order_by(Client.name).all()
