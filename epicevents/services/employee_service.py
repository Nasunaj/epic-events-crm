"""Employee business logic (service layer)"""

import re
from sqlalchemy.orm import Session
from epicevents.models import Employee, Role
from epicevents.security import hash_password

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


class DuplicateError(Exception):
    """Raised when a email or employee number already exists"""


def _validate_password(password: str, confirmation: str | None) -> None:
    """Validate password strength and confirmation."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Mot de passe trop court: minimum {MIN_PASSWORD_LENGTH} " f"caractères."
        )
    if confirmation is not None and confirmation != password:
        raise ValueError("La confirmation du mot de passe ne correspond pas.")


def create_employee(
    session: Session,
    email: str,
    employee_number: str,
    name: str,
    role_name: str,
    password: str,
    password_confirmation: str | None = None,
) -> Employee:
    """Create a collaborator. Hashes the password, never stores plaintext."""
    # Validation avant toute écriture
    if not email or not EMAIL_RE.match(email):
        raise ValueError(f"Email invalid: {email!r}")

    _validate_password(password, password_confirmation)

    # Unité (ORM)
    if session.query(Employee).filter_by(email=email).first():
        raise DuplicateError(f"Email déjà pris: {email!r}")
    if session.query(Employee).filter_by(employee_number=employee_number).first():
        raise DuplicateError(f"Numéro déjà pris: {employee_number!r}")

    # Récupérer le rôle
    role = session.query(Role).filter_by(name=role_name).first()
    if role is None:
        raise ValueError(f"Role inconnu : {role_name!r}")

    # Hacher avant de toucher à la session. Le mdp en clair n'atteint
    # jamais la session/modèle
    password_hash = hash_password(password)
    # créer, ajouter puis commiter
    employee = Employee(
        email=email,
        employee_number=employee_number,
        name=name,
        role=role,
        password_hash=password_hash,
    )
    session.add(employee)
    session.commit()
    return employee
