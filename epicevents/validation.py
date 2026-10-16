"""Shared field validation rules."""

import re
from decimal import Decimal, InvalidOperation
from epicevents.exceptions import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def require_non_empty(value: str, label: str) -> None:
    """Raise ValidationError if value is empty/blank."""
    if not value or not value.strip():
        raise ValidationError(f"Le champ {label} ne peut pas être vide.")


def require_non_empty_if_present(field: str, fields_to_update: dict) -> None:
    """Raise ValidationError if `field` is in the update and blank."""
    if field in fields_to_update:
        require_non_empty(fields_to_update[field], field)


def require_amount(value: str, label: str) -> Decimal:
    """Validate a monetary amount string and return it as Decimal.

    Why Decimal and never float: binary floats cannot represent most
    decimal fractions exactly (0.1 + 0.2 != 0.3), which is unacceptable
    for money. Decimal computes in base 10, exactly.
    """
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValidationError(f"Montant invalide : {value!r}")
    # ci-dessous au cas où saisie inf ou nan car inf Decimal pas d'exception
    # et pour nan lève une InvalidOperation non attrapée
    if not amount.is_finite():
        raise ValidationError(f"Montant invalide : {value!r}")
    if amount < 0:
        raise ValidationError(f"Le montant {label} ne peut pas être négatif.")
    return amount
