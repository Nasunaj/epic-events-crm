"""Tests for role-based permission checks."""

from epicevents.auth import check_permission


def test_gestion_allowed_for_gestion(session, make_employee, role_ges):
    """Test check permission for gestion role."""
    employee = make_employee(role_name="gestion")  # ← mot-clé, chaîne
    assert check_permission(employee, ("gestion",)) is True


def test_commercial_denied_for_gestion_only(session, make_employee, role_com):
    """Test permission denied for commercial role."""
    employee = make_employee(role_name="commercial")
    assert check_permission(employee, ("gestion",)) is False


def test_commercial_allowed_among_several_roles(session, make_employee, role_com):
    """Test permission allowed for commercial role in tuple several roles
    allowed."""
    employee = make_employee(role_name="commercial")
    assert check_permission(employee, ("gestion", "commercial")) is True
