"""Seed the reference roles defined by the brief (idempotent).

Creates any missing role among gestion / commercial / support.
Safe to run any number of times: existing roles are never touched.

Usage (from project root, venv activated):
    python -m scripts.seed_roles
"""

from epicevents.database import get_session
from epicevents.models import Role

ROLES = ("gestion", "commercial", "support")


def seed_roles(session) -> list[str]:
    """Testable logic: create missing roles, return created names."""
    created = []
    for role_name in ROLES:
        if session.query(Role).filter_by(name=role_name).first() is None:
            session.add(Role(name=role_name))
            created.append(role_name)
    session.commit()
    return created


if __name__ == "__main__":
    session = get_session()
    try:
        created = seed_roles(session)
        if created:
            print(f"Rôles créés : {', '.join(created)}")
        else:
            print("Tous les rôles existent déjà (aucune action).")
    finally:
        session.close()
