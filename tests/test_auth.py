"""Tests for the authentication service."""

import pytest
from epicevents.services.auth_service import (
    AuthenticationError,
    get_current_employee,
    login,
)
from epicevents.token_store import read_token

EMAIL = "c.josh@epicevents.com"
PASSWORD = "AZERTYUI"


def test_login_success_returns_employee(session, make_employee, isolated_store):
    """Test that a successful login is returned"""
    employee = make_employee(email=EMAIL, password=PASSWORD)
    logged = login(session, EMAIL, PASSWORD)
    assert logged.id == employee.id


def test_login_stores_token(session, make_employee, isolated_store):
    """Test token stored is correctly read"""
    make_employee(email=EMAIL, password=PASSWORD)
    login(session, EMAIL, PASSWORD)
    assert read_token() is not None


def test_login_wrong_password(session, make_employee, isolated_store):
    """Test AuthenticationError wrong password"""
    make_employee(email=EMAIL, password=PASSWORD)
    with pytest.raises(AuthenticationError):
        login(session, EMAIL, "azedcvfk")


def test_login_unknown_email(session, make_employee, isolated_store):
    """Test AuthenticationError unknown email"""
    make_employee(email=EMAIL, password=PASSWORD)
    with pytest.raises(AuthenticationError):
        login(session, "a@azer.com", PASSWORD)


def test_error_message_is_generic_no_enumeration(
    session, make_employee, isolated_store
):
    """Wrong password and unknown email raise the exact SAME message."""
    make_employee(email=EMAIL, password=PASSWORD)
    with pytest.raises(AuthenticationError) as exc_info:
        login(session, EMAIL, "azedcvfk")
    wrong_password_message = str(exc_info.value)
    with pytest.raises(AuthenticationError) as exc_info:
        login(session, "a@azer.com", PASSWORD)
    unknown_email_message = str(exc_info.value)
    assert wrong_password_message == unknown_email_message


def test_get_current_employee_after_login(session, make_employee, isolated_store):
    """Verify current employee is returned after login"""
    employee = make_employee(email=EMAIL, password=PASSWORD)
    login(session, EMAIL, PASSWORD)
    current_employee = get_current_employee(session)
    assert current_employee is not None
    assert current_employee.id == employee.id


def test_get_current_employee_without_token(session, isolated_store):
    """Test get_current_employee without token"""
    assert get_current_employee(session) is None
