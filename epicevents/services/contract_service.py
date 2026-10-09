"""Contract reading services: listings and display filters.

Read access is universal (all authenticated employees — see policies).
The filters implemented here are display conveniences required by the
brief: unsigned contracts, and contracts not fully paid yet.
"""

from sqlalchemy.orm import Session

from epicevents.models import Contract


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
