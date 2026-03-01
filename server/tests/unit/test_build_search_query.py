"""Unit tests for build_search_query in routers/events/search.py.

Each test covers exactly one behaviour. Date assertions use dt_from_iso to
derive expected values from the same source as the function under test,
so tests aren't sensitive to isoformat representation choices.
"""
import pytest

from app.helpers.date import dt_from_iso
from app.routers.events.search import build_search_query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_bool(query: dict) -> dict:
    return query["bool"]


def get_filters(query: dict) -> list:
    return get_bool(query).get("filter", [])


def get_range_filter(query: dict) -> dict:
    """Return the timestamp range dict from the filter list, or {} if absent."""
    for f in get_filters(query):
        if "range" in f:
            return f["range"]["timestamp"]
    return {}


# ---------------------------------------------------------------------------
# must / multi_match
# ---------------------------------------------------------------------------

def test_search_term_is_embedded_in_must():
    """The q string should always appear in the multi_match query."""
    result = build_search_query("browser", None, None, None, None)
    multi_match = get_bool(result)["must"]["multi_match"]
    assert multi_match["query"] == "browser"
    assert multi_match["fields"] == ["metadata.*"]


# ---------------------------------------------------------------------------
# filter list presence / absence
# ---------------------------------------------------------------------------

def test_no_filters_omits_filter_key():
    """When no optional args are supplied, the 'filter' key must be absent."""
    result = build_search_query("anything", None, None, None, None)
    assert "filter" not in get_bool(result)


def test_all_filter_types_produce_three_entries():
    """event_type + user_id + date range should produce exactly three filter entries."""
    result = build_search_query(
        "x", "click", "user-1", "2024-01-01T00:00:00Z", "2024-01-31T00:00:00Z"
    )
    assert len(get_filters(result)) == 3


# ---------------------------------------------------------------------------
# individual filters
# ---------------------------------------------------------------------------

def test_event_type_adds_term_filter():
    """event_type should produce a term filter on the 'type' field."""
    result = build_search_query("x", "click", None, None, None)
    filters = get_filters(result)
    assert {"term": {"type": "click"}} in filters


def test_user_id_adds_term_filter():
    """user_id should produce a term filter on the 'user_id' field."""
    result = build_search_query("x", None, "user-99", None, None)
    filters = get_filters(result)
    assert {"term": {"user_id": "user-99"}} in filters


# ---------------------------------------------------------------------------
# date range filter
# ---------------------------------------------------------------------------

def test_start_date_only_sets_gte_not_lte():
    """Only start_date should produce a range with gte but no lte."""
    start = "2024-01-01T00:00:00Z"
    result = build_search_query("x", None, None, start, None)
    date_range = get_range_filter(result)
    assert date_range["gte"] == dt_from_iso(start).isoformat()
    assert "lte" not in date_range


def test_end_date_only_sets_lte_not_gte():
    """Only end_date should produce a range with lte but no gte."""
    end = "2024-01-31T23:59:59Z"
    result = build_search_query("x", None, None, None, end)
    date_range = get_range_filter(result)
    assert date_range["lte"] == dt_from_iso(end).isoformat()
    assert "gte" not in date_range


def test_full_date_range_sets_both_bounds():
    """Both start_date and end_date should produce a range with both gte and lte."""
    start = "2024-01-01T00:00:00Z"
    end = "2024-01-31T23:59:59Z"
    result = build_search_query("x", None, None, start, end)
    date_range = get_range_filter(result)
    assert "gte" in date_range
    assert "lte" in date_range


# ---------------------------------------------------------------------------
# error handling
# ---------------------------------------------------------------------------

def test_invalid_date_raises_value_error():
    """An unparseable date string should propagate a ValueError."""
    with pytest.raises(ValueError, match="bad-date"):
        build_search_query("x", None, None, "bad-date", None)
