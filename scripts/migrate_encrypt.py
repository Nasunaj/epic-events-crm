"""Migrate existing plaintext values to encrypted values (one-shot).

Reads raw values with plain SQL (bypassing the encrypted type, which
cannot decrypt old plaintext), encrypts each value in Python with the
same AesEngine used by the models, then writes the ciphertext back.

Usage: python -m scripts.migrate_encrypt
"""

from sqlalchemy import text, String

from epicevents.database import get_session
from epicevents.models import ENCRYPTION_KEY
from sqlalchemy_utils.types.encrypted.encrypted_type import (
    StringEncryptedType,
    AesEngine,
)

# Le type est instancié exactement comme dans les modèles : c'est le
# MÊME moteur, donc le chiffré produit est celui que les modèles
# sauront déchiffrer à la lecture.
_ENCRYPTOR = StringEncryptedType(String, ENCRYPTION_KEY, AesEngine)

FIELDS = [
    ("employee", "id", "employee_number"),
    ("employee", "id", "name"),
    ("employee", "id", "email"),
    ("client", "id", "name"),
    ("client", "id", "email"),
    ("client", "id", "phone"),
    ("client", "id", "company_name"),
    ("event", "id", "name"),
    ("event", "id", "location"),
    ("event", "id", "note"),
]


def migrate(session) -> int:
    """Encrypt every plaintext value; skip values already encrypted."""
    total = 0
    for table, pk, column in FIELDS:
        rows = session.execute(
            text(f"SELECT {pk} AS id, CAST({column} AS TEXT) AS val " f'FROM "{table}"')
        ).fetchall()
        for row in rows:
            if row.val is None:
                continue
            # Idempotence : si la valeur se DÉchiffre, c'est déjà du chiffré
            # (employés traités au passage précédent) → on saute.
            try:
                _ENCRYPTOR.process_result_value(row.val, None)
                continue
            except Exception:
                pass  # le déchiffrement échoue = c'est encore du clair
            encrypted = _ENCRYPTOR.process_bind_param(row.val, None)
            session.execute(
                text(f'UPDATE "{table}" SET {column} = :val WHERE {pk} = :id'),
                {"val": encrypted, "id": row.id},
            )
            total += 1
    session.commit()
    return total


if __name__ == "__main__":
    session = get_session()
    try:
        n = migrate(session)
        print(f"Migration terminée : {n} valeurs chiffrées.")
    finally:
        session.close()
