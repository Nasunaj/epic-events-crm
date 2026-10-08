"""Tests for the admin bootstrap logic (scripts/create_admin.py)."""

from scripts.create_admin import GESTION, bootstrap_admin
from epicevents.models import Role


def test_bootstrap_creates_role_and_admin(session):
    """First run: the gestion role is created along with the admin."""
    ok_first_run = bootstrap_admin(
        session,
        email="admin@epicevents.com",
        employee_number="E001",
        name="Josh C",
        password="AZERTYUI",
        password_confirmation="AZERTYUI",
    )
    assert ok_first_run is True
    # Rôle bien créé par ensure_role
    role = session.query(Role).filter_by(name=GESTION).first()
    assert role is not None


def test_bootstrap_is_idempotent_on_role(session):
    """Relaunching does not duplicate the gestion role.

    Given a fresh database, bootstrapping twice (e.g. an installer
    running the script again) must keep exactly one 'gestion' role.
    """
    # base vierge, aucun rôle gestion (précondition)
    assert session.query(Role).filter_by(name=GESTION).count() == 0

    # premier lancement du script
    ok = bootstrap_admin(
        session,
        email="a@epicevents.com",
        employee_number="E001",
        name="A",
        password="AZERTYUI",
        password_confirmation="AZERTYUI",
    )

    # le rôle est créé, l'appel a réussi
    assert ok is True
    assert session.query(Role).filter_by(name=GESTION).count() == 1

    # second lancement (relance, autre admin)
    ok2 = bootstrap_admin(
        session,
        email="b@epicevents.com",
        employee_number="E002",
        name="B",
        password="AZERTYUI",
        password_confirmation="AZERTYUI",
    )

    # succès, mais toujours UN SEUL rôle gestion
    assert ok2 is True
    assert session.query(Role).filter_by(name=GESTION).count() == 1


def test_bootstrap_duplicate_return_false(session):
    """An already-used mail return False, without crashing"""
    args = dict(
        email="a@epicevents.com",
        employee_number="E001",
        name="A",
        password="AZERTYUI",
        password_confirmation="AZERTYUI",
    )
    assert bootstrap_admin(session, **args) is True
    args.pop("employee_number")  # on retire la clé qu'on va redéfinir
    assert bootstrap_admin(session, employee_number="E002", **args) is False


def test_bootstrap_too_short_password_returns_false(session):
    """A too-short password is rejected cleanly."""
    ok = bootstrap_admin(
        session,
        email="a@epicevents.com",
        employee_number="E001",
        name="A",
        password="AZERTY",
        password_confirmation="AZERTY",
    )
    assert ok is False
