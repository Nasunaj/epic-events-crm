"""Tests for the reference-role seeding (scripts/seed_roles.py)."""

from scripts.seed_roles import seed_roles
from epicevents.models import Role


def test_seed_creates_all_three_roles(session):
    """First run: the three brief roles are created."""
    created = seed_roles(session)
    assert set(created) == {"gestion", "commercial", "support"}
    assert session.query(Role).count() == 3


def test_seed_is_idempotent(session):
    """Relaunching creates nothing and touches nothing."""
    seed_roles(session)
    created_second_run = seed_roles(session)
    # rien de créé au second passage, toujours 3 rôles
    assert created_second_run == []
    assert session.query(Role).count() == 3


def test_seed_fills_only_missing(session):
    """Partial database: only the missing roles are added."""
    session.add(Role(name="gestion"))
    session.commit()
    created = seed_roles(session)
    assert set(created) == {"commercial", "support"}
    assert session.query(Role).count() == 3
