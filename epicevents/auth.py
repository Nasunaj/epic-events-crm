"""Authorization: role-based permission checks.

Authentication (who are you?) is resolved by auth_service; this module
answers the next question: is this employee allowed to do this action?
"""

from epicevents.models import Employee


class PermissionDeniedError(Exception):
    """The authenticated employee's role does not allow this action."""


def check_permission(employee: Employee, allowed_roles: tuple[str, ...]) -> bool:
    """Return True if the employee's role is in the allowed roles"""
    return employee.role.name in allowed_roles
