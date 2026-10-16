"""Contract reading services: listings and display filters.

Read access is universal (all authenticated employees — see policies).
The filters implemented here are display conveniences required by the
brief: unsigned contracts, and contracts not fully paid yet.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from epicevents.auth import check_permission
from epicevents.exceptions import (
    PermissionDeniedError,
    NotFoundError,
    ValidationError,
    NotOwnedError,
)
from epicevents.models import Contract, Employee, Client
from epicevents.policies import CONTRACT_CREATORS, CONTRACT_UPDATERS
from epicevents.validation import require_amount, require_non_empty_if_present


def _base_query(session: Session):
    """Common ordered query shared by all contract listings."""
    return session.query(Contract).order_by(Contract.creation_date.desc())


def list_contracts(session: Session) -> list[Contract]:
    """List every contract, most recent first."""
    return _base_query(session).all()


def list_unsigned_contracts(session: Session) -> list[Contract]:
    """List contracts that have not been signed yet."""
    return _base_query(session).filter(Contract.is_signed.is_(False)).all()


def list_unpaid_contracts(session: Session) -> list[Contract]:
    """List contracts whose remaining amount is greater than zero."""
    return _base_query(session).filter(Contract.remaining_amount > 0).all()


# _____writing_____________
def create_contract(
    session: Session,
    employee: Employee,
    client_id: int,
    total_amount: str,
    remaining_amount: str,
    is_signed: bool = False,
) -> Contract:
    """Create a contract. Gestion only, inherits the client's commercial.
    Business rules:
    - remaining_amount may not exceed total_amount;
    - an UNSIGNED contract may not have partial payment
    (remaining < total): money only flows after signature."""

    if not check_permission(employee, CONTRACT_CREATORS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas créer de contrat."
        )

    client = session.get(Client, client_id)
    if client is None:
        raise NotFoundError(f"Client introuvable : {client_id}")

    total = require_amount(total_amount, "total")
    remaining = require_amount(remaining_amount, "solde restant")
    if remaining > total:
        raise ValidationError("Le restant à payer dépasse le montant total.")

    if is_signed is False and remaining < total:
        raise ValidationError(
            "Un contrat doit être signé avant tout paiement. "
            "Signez le contrat d'abord (is_signed=True)."
        )

    contract = Contract(
        client=client,
        commercial=client.commercial,
        total_amount=total,
        remaining_amount=remaining,
        is_signed=is_signed,
        creation_date=datetime.now(timezone.utc),
    )

    session.add(contract)
    session.commit()
    return contract


UPDATABLE_FIELDS = {"is_signed", "total_amount", "remaining_amount", "client_id"}


def update_contract(
    session: Session, employee: Employee, contract_id: int, **fields_to_update
) -> Contract:
    """Update an existing contract."""
    if not check_permission(employee, CONTRACT_UPDATERS):
        raise PermissionDeniedError(
            f"Le rôle {employee.role.name!r} ne peut pas modifier un contrat."
        )
    if not fields_to_update:
        raise ValidationError("Aucun champ à modifier.")

    contract = session.get(Contract, contract_id)
    if contract is None:
        raise NotFoundError(f"Contrat introuvable : {contract_id}")

    # Le champ client_id est le plus critique : il redéfinit le périmètre
    # même du contrat. Seul le service de gestion peut réaffecter un contrat
    # (correction d'erreur de saisie, fusion de clients) ; dans le cas contraire,
    # un commercial pourrait déplacer des contrats pour contourner son propre périmètre.
    if "client_id" in fields_to_update and employee.role.name != "gestion":
        raise PermissionDeniedError(
            "Seul le rôle gestion peut rattacher un contrat à un autre client."
        )

    if employee.role.name != "gestion" and contract.commercial_id != employee.id:
        raise NotOwnedError("Ce contrat n'est pas dans votre périmètre.")

    for field in fields_to_update:
        if field not in UPDATABLE_FIELDS:
            raise ValidationError(f"Champ non modifiable : {field!r}")

    if "is_signed" in fields_to_update and not isinstance(
        fields_to_update["is_signed"], bool
    ):
        raise ValidationError("is_signed doit être un booléen.")

    require_non_empty_if_present("total_amount", fields_to_update)
    require_non_empty_if_present("remaining_amount", fields_to_update)

    if "total_amount" in fields_to_update:
        total = require_amount(fields_to_update["total_amount"], "total")
    else:
        total = contract.total_amount

    if "remaining_amount" in fields_to_update:
        remaining = require_amount(
            fields_to_update["remaining_amount"], "solde restant"
        )
    else:
        remaining = contract.remaining_amount
    signed = fields_to_update.get("is_signed", contract.is_signed)

    new_client = None
    if "client_id" in fields_to_update:
        new_client = session.get(Client, fields_to_update["client_id"])
        if new_client is None:
            raise NotFoundError(
                f"Client introuvable : {fields_to_update['client_id']!r}"
            )

    # Validations avant écriture
    if remaining > total:
        raise ValidationError("Le restant à payer dépasse le montant total.")

    if signed is False and remaining < total:
        raise ValidationError(
            "Un contrat doit être signé avant tout paiement. "
            "Signez le contrat d'abord (is_signed=True)."
        )

    # écriture
    contract.total_amount = total
    contract.remaining_amount = remaining
    if "is_signed" in fields_to_update:
        contract.is_signed = signed
    if new_client is not None:
        contract.client = new_client
        contract.commercial = new_client.commercial

    session.commit()
    return contract
