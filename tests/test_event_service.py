"""Tests for event reading services (personal and workflow filters)."""

from epicevents.services.event_service import (
    list_events,
    list_events_for_commercial,
    list_events_for_support,
    list_events_without_support,
)


def test_list_events_returns_all(session, event, event2):
    """Every event shows up in the global listing."""
    assert len(list_events(session)) == 2


def test_without_support_filter_selects_unassigned(session, event, event2):
    """Only events with support_id IS NULL appear."""
    without = list_events_without_support(session)
    assert len(without) == 1
    assert without[0].id == event2.id  # event2: support=None


def test_for_support_returns_own_events(session, event, event2, support):
    """A support sees (via the filter) only the events assigned to them."""
    own = list_events_for_support(session, support)
    assert len(own) == 1
    assert own[0].id == event.id


def test_for_commercial_returns_own_contract_events(session, event, event2, commercial):
    """The commercial's filter returns events on their clients' contracts."""
    own = list_events_for_commercial(session, commercial)
    print(own)
    assert len(own) == 2
    # assert own[0].id == event.id
    # assert own[1].id == event2.id
    assert {e.id for e in own} == {event.id, event2.id}
