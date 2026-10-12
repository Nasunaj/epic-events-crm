"""Employee business logic (service layer)"""

import re
from sqlalchemy.orm import Session

from epicevents.auth import check_permission
from epicevents.exceptions import (
    PermissionDeniedError,
    ValidationError,
    DuplicateError,
    NotFoundError,
)
from epicevents.models import Employee, Role
from epicevents.policies import EMPLOYEE_MANAGERS
from epicevents.security import hash_password

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def _validate_password(password: str, confirmation: str | None = None) -> None:
    """Validate password strength and confirmation."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Mot de passe trop court: minimum {MIN_PASSWORD_LENGTH} " f"caractères."
        )
    if confirmation is not None and confirmation != password:
        raise ValidationError("La confirmation du mot de passe ne correspond pas.")


def _validate_email(
    session: Session, email: str, exclude_id: int | None = None
) -> None:
    """Check email format and uniqueness (excluding one employee id)."""
    if not email or not EMAIL_RE.match(email):
        raise ValidationError(f"Email invalide : {email!r}")
    query = session.query(Employee).filter(Employee.email == email)
    if exclude_id is not None:
        query = query.filter(Employee.id != exclude_id)
    if query.first():
        raise DuplicateError(f"Email déjà pris : {email!r}")


def _validate_employee_number(
    session: Session, number: str, exclude_id: int | None = None
) -> None:
    """Check employee number uniqueness (excluding one employee id)."""
    query = session.query(Employee).filter(Employee.employee_number == number)
    if exclude_id is not None:
        query = query.filter(Employee.id != exclude_id)
    if query.first():
        raise DuplicateError(f"Numéro déjà pris : {number!r}")


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

    _validate_email(session, email)
    _validate_password(password, password_confirmation)
    _validate_employee_number(session, employee_number)

    role = session.query(Role).filter_by(name=role_name).first()
    if role is None:
        raise ValidationError(f"Rôle inconnu : {role_name!r}")

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


# Piège de sécurité du **fields : une faille classique s'appelle mass
# assignment. L'utilisateur malveillant envoie un champ qu'il ne devrait pas
# pouvoir changer (ex : un commercial qui enverrait role_id=1 pour devenir
# gestionnaire !). La parade obligatoire : une liste blanche de champs
# autorisés, et on ignore/rejette tout le reste
UPDATABLE_FIELDS = {"name", "email", "employee_number", "role_name", "password"}


def update_employee(
    session: Session, employee: Employee, target_employee_id: int, **fields_to_update
) -> Employee:
    """Update a collaborator. Gestion only (per the brief).

    Whitelist (mass-assignment protection): only UPDATABLE_FIELDS are
    accepted — any other field raises ValidationError (rejected loudly
    rather than silently ignored).
    """

    # Rôle
    if not check_permission(employee, EMPLOYEE_MANAGERS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas modifier un collaborateur."
        )

    if not fields_to_update:
        raise ValidationError("Aucun champ à modifier.")

    # Cible
    target = session.get(Employee, target_employee_id)
    if target is None:
        raise NotFoundError(f"Collaborateur introuvable : {target_employee_id}")

    # Whitelist
    for field in fields_to_update:
        if field not in UPDATABLE_FIELDS:
            raise ValidationError(f"Champ non modifiable : {field!r}")
    # Validation (avant toute écriture — vigilance n°1 du brief)
    if "password" in fields_to_update:
        # Pas de confirmation en update : la CLI demandera la double
        # saisie, le service reçoit une valeur déjà confirmée.
        _validate_password(fields_to_update["password"])
    if "name" in fields_to_update and not fields_to_update["name"].strip():
        raise ValidationError("Le nom ne peut pas être vide.")
    if "email" in fields_to_update:
        _validate_email(session, fields_to_update["email"], exclude_id=target.id)
    if "employee_number" in fields_to_update:
        _validate_employee_number(
            session, fields_to_update["employee_number"], exclude_id=target.id
        )
    new_role = None
    if "role_name" in fields_to_update:
        new_role = (
            session.query(Role).filter_by(name=fields_to_update["role_name"]).first()
        )
        if new_role is None:
            raise ValidationError(f"Rôle inconnu : {fields_to_update['role_name']!r}")
    # Ecriture (tout est validé : on peut écrire)
    if "password" in fields_to_update:
        target.password_hash = hash_password(fields_to_update["password"])
    if new_role is not None:
        target.role = new_role
    for field in ("name", "email", "employee_number"):
        if field in fields_to_update:
            setattr(target, field, fields_to_update[field])
    session.commit()
    return target
