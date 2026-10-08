"""One-shot admin bootstrap script. Run manually at install time.

Creates the FIRST gestion (admin) account, which is needed because
employee creation is restricted to the gestion role — and an empty
database has no gestion user to start with.

Usage (from project root, venv activated):
    python -m scripts.create_admin

Security notes:
- Run once, at installation time, by the person installing the
  application (assumed to have administrator access to the machine).
- For everyday use, do NOT create accounts with this script: use the
  application itself (create-employee command, restricted to the
  gestion role, authenticated and traceable).
- Running it again with a new email/number creates ANOTHER gestion
  account; running it with an already used email/number is rejected
  cleanly and changes nothing.
"""

# DÉLÉGATION À LA COUCHE SERVICE
# Ce script est une "interface" : il parle à l'humain (input/getpass)
# et délègue TOUTES les règles métier à create_employee.
#
# Il ne sait pas (et ne doit pas savoir) comment sont faites les choses :
# validation de l'email, force du mot de passe, vérification d'unicité,
# hachage Argon2id, insertion en base. Il transmet des données brutes
# et reçoit soit un employé, soit une erreur métier.
#
# Pourquoi c'est vital :
# 1. Le hachage du mot de passe existe à UN seul endroit (le service).
#    Impossible de créer un employé sans passer par lui -> impossible
#    d'oublier le hachage (un mot de passe en clair ne peut pas être
#    inséré "par accident").
# 2. Changer d'algorithme (Argon2 -> bcrypt) = modifier 1 seul fichier.
# 3. Le script est testable : pas d'interaction dans la logique.
#
# La sécurité repose sur l'architecture, pas sur la vigilance.

import getpass  # saisie masquée

from epicevents.database import get_session  # fabrique de notre session
from epicevents.models import Role
from epicevents.services.employee_service import (
    DuplicateError,  # Notre erreur métier
    create_employee,  # Notre service
)

GESTION = "gestion"


def ensure_role(session, role_name: str) -> Role:
    """Return the role, creating it if missing (idempotent)."""
    role = session.query(Role).filter_by(name=role_name).first()
    if role is None:
        role = Role(name=role_name)
        session.add(role)
        session.commit()
    return role


def bootstrap_admin(
    session,
    email: str,
    employee_number: str,
    name: str,
    password: str,
    password_confirmation: str,
) -> bool:
    """Testable logic: create the first gestion admin.

    Returns True on success, False if the account already exists.
    """
    role = ensure_role(session, GESTION)
    try:
        employee = create_employee(
            session,
            email=email,
            employee_number=employee_number,
            name=name,
            password=password,
            password_confirmation=password_confirmation,
            role_name=role.name,
        )
    except DuplicateError as exc:
        print(f"Compte déjà existant : {exc}")
        return False
    except ValueError as exc:
        print(f"Données invalides : {exc}")
        return False
    print(f"Admin créé : {employee.name} ({employee.email})")
    return True


if __name__ == "__main__":
    session = get_session()
    try:
        bootstrap_admin(
            session,
            email=input("Email de l'admin : "),
            employee_number=input("Numéro d'employé : "),
            name=input("Nom complet : "),
            password=getpass.getpass("Mot de passe : "),
            password_confirmation=getpass.getpass("Confirmation : "),
        )
    finally:
        session.close()
