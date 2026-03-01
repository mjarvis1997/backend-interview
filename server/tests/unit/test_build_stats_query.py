"""Unit tests for build_stats_query in routers/events/stats.py.

Each test covers exactly one behaviour. Expected datetime values are derived
via dt_from_iso so tests stay in sync with production parsing logic.
"""
import pytest

from app.helpers.date import dt_from_iso
from app.routers.events.stats import build_stats_query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_match(pipeline: list) -> dict:
    """Return the $match stage content, or {} if no match stage is present."""
    for stage in pipeline:
        if "$match" in stage:
            return stage["$match"]
    return {}


def get_group(pipeline: list) -> dict:
    return next(s["$group"] for s in pipeline if "$group" in s)


def get_sort(pipeline: list) -> dict:
    return next(s["$sort"] for s in pipeline if "$sort" in s)


def get_time_range_start(pipeline: list):
    """Return the time_range_start expression from the $group _id."""
    return get_group(pipeline)["_id"]["time_range_start"]


# ---------------------------------------------------------------------------
# Pipeline length / $match presence
# ---------------------------------------------------------------------------

def test_no_dates_omits_match_stage():
    """Without date filters the pipeline should have no $match stage."""
    pipeline = build_stats_query(None, None, "daily")
    assert not any("$match" in s for s in pipeline)


def test_no_dates_produces_two_stages():
    """Without date filters the pipeline should have exactly $group and $sort."""
    pipeline = build_stats_query(None, None, "daily")
    assert len(pipeline) == 2


def test_with_dates_produces_three_stages():
    """With at least one date filter the pipeline should have $match, $group, $sort."""
    pipeline = build_stats_query("2024-01-01T00:00:00Z", None, "daily")
    assert len(pipeline) == 3


# ---------------------------------------------------------------------------
# $match stage — date bounds
# ---------------------------------------------------------------------------

def test_start_date_sets_gte():
    """start_date should appear as $gte in the timestamp match."""
    start = "2024-01-01T00:00:00Z"
    pipeline = build_stats_query(start, None, None)
    assert get_match(pipeline)["timestamp"]["$gte"] == dt_from_iso(start)


def test_end_date_sets_lte():
    """end_date should appear as $lte in the timestamp match."""
    end = "2024-01-31T23:59:59Z"
    pipeline = build_stats_query(None, end, None)
    assert get_match(pipeline)["timestamp"]["$lte"] == dt_from_iso(end)


def test_full_date_range_sets_both_bounds():
    """Both dates provided should set both $gte and $lte on timestamp."""
    start = "2024-01-01T00:00:00Z"
    end = "2024-01-31T23:59:59Z"
    pipeline = build_stats_query(start, end, None)
    ts = get_match(pipeline)["timestamp"]
    assert "$gte" in ts and "$lte" in ts


# ---------------------------------------------------------------------------
# time_bucket → $dateTrunc unit
# ---------------------------------------------------------------------------

def test_hourly_bucket_unit():
    pipeline = build_stats_query(None, None, "hourly")
    assert get_time_range_start(pipeline)["$dateTrunc"]["unit"] == "hour"


def test_daily_bucket_unit():
    pipeline = build_stats_query(None, None, "daily")
    assert get_time_range_start(pipeline)["$dateTrunc"]["unit"] == "day"


def test_weekly_bucket_unit():
    pipeline = build_stats_query(None, None, "weekly")
    assert get_time_range_start(pipeline)["$dateTrunc"]["unit"] == "week"


def test_weekly_bucket_starts_on_monday():
    """Weekly bucket must use Monday as the start of week."""
    pipeline = build_stats_query(None, None, "weekly")
    assert get_time_range_start(
        pipeline)["$dateTrunc"]["startOfWeek"] == "monday"


def test_none_bucket_produces_null_time_range_start():
    """No time_bucket should leave time_range_start as None in the $group _id."""
    pipeline = build_stats_query(None, None, None)
    assert get_time_range_start(pipeline) is None


# ---------------------------------------------------------------------------
# $group structure
# ---------------------------------------------------------------------------

def test_group_counts_with_sum():
    """$group should always accumulate a count via $sum: 1."""
    pipeline = build_stats_query(None, None, "daily")
    assert get_group(pipeline)["count"] == {"$sum": 1}


def test_group_id_includes_event_type():
    """$group _id must include the event type field."""
    pipeline = build_stats_query(None, None, "daily")
    assert get_group(pipeline)["_id"]["type"] == "$type"


# ---------------------------------------------------------------------------
# $sort is always the last stage
# ---------------------------------------------------------------------------

def test_sort_is_last_stage():
    pipeline = build_stats_query(None, None, "daily")
    assert "$sort" in pipeline[-1]


def test_sort_orders_by_time_range_descending():
    pipeline = build_stats_query(None, None, "daily")
    assert get_sort(pipeline)["_id.time_range_start"] == -1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_invalid_start_date_raises_value_error():
    with pytest.raises(ValueError, match="bad-date"):
        build_stats_query("bad-date", None, None)


def test_invalid_end_date_raises_value_error():
    with pytest.raises(ValueError, match="also-bad"):
        build_stats_query(None, "also-bad", None)
