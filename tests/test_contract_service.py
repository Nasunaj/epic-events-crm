"""Tests for contract reading services (display filters)."""

from epicevents.services.contract_service import (
    list_contracts,
    list_unsigned_contracts,
    list_unpaid_contracts,
)


def test_list_contracts_returns_all(session, contract, contract2):
    """Every contract shows up in the global listing."""
    assert len(list_contracts(session)) == 2


def test_unsigned_filter_selects_only_unsigned(session, contract, contract2):
    """Only the unsigned contract appears in the unsigned listing."""
    unsigned = list_unsigned_contracts(session)
    assert len(unsigned) == 1
    assert unsigned[0].id == contract2.id


def test_unpaid_filter_selects_only_unpaid(session, contract, contract2):
    """Only the contract with remaining_amount > 0 appears."""
    unpaid = list_unpaid_contracts(session)
    assert len(unpaid) == 1
    assert unpaid[0].id == contract.id


def test_signed_fully_paid_contract_appears_only_in_global_list(
    session, contract, contract2
):
    """A signed, fully paid contract is in the global list,
    but in neither filter (it does not match them)."""
    global_ids = [c.id for c in list_contracts(session)]
    unsigned_ids = [c.id for c in list_unsigned_contracts(session)]
    unpaid_ids = [c.id for c in list_unpaid_contracts(session)]

    assert contract.id in global_ids  # il existe, liste globale
    assert contract.id not in unsigned_ids  # signé,pas dans les non-signés
    assert contract.id in unpaid_ids  # pas soldé

    assert contract2.id not in unpaid_ids  # soldé, pas dans les impayés
