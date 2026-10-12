"""Shared field validation rules."""

import re

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
