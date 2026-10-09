"""Authentication service: login and current-user resolution."""

from epicevents.models import Employee
from epicevents.security import create_token, verify_password, decode_token
from epicevents.token_store import read_token, save_token


class AuthenticationError(Exception):
    """Invalid credentials (generic message on purpose)."""


def login(session, email: str, password: str) -> Employee:
    """Authenticate an employee and store their JWT on disk.

    Raises AuthenticationError on wrong email or password
    (same generic message for both: no user enumeration).
    """
    employee = session.query(Employee).filter_by(email=email).first()
    if employee is None or not verify_password(password, employee.password_hash):
        raise AuthenticationError("Identifiants incorrects.")

    token = create_token(employee_id=employee.id, role=employee.role.name)
    save_token(token)
    return employee


def get_current_employee(session) -> Employee | None:
    """Resolve the logged-in employee from the stored token.

    Returns None if no token is stored. Raises jwt.ExpiredSignatureError
    or jwt.InvalidTokenError if the token is stale/tampered (the caller
    should prompt for re-login).
    """
    token = read_token()
    if token is None:
        return None
    payload = decode_token(token)
    # session.get(Employee, int(payload["sub"])) : le raccourci ORM
    # « charge-moi l'objet par sa clé primaire ». Le int(...) car sub était un
    # str (le standard JWT). Retourne None si l'employé a été supprimé de la
    # base depuis => cohérent avec la signature Employee | None.
    return session.get(Employee, int(payload["sub"]))
