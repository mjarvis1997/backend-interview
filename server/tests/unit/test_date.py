from datetime import datetime, timezone, timedelta

import pytest

from app.helpers.date import dt_from_iso


def test_utc_z_suffix():
    """'Z' should be treated as UTC (+00:00)."""
    result = dt_from_iso("2024-01-15T10:30:00Z")
    assert result == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


def test_explicit_positive_offset():
    """Explicit positive UTC offset should be preserved."""
    result = dt_from_iso("2024-01-15T10:30:00+05:00")
    assert result.utcoffset() == timedelta(hours=5)
    assert result.hour == 10


def test_naive_datetime():
    """ISO string with no timezone info should produce a naive datetime."""
    result = dt_from_iso("2024-01-15T10:30:00")
    assert result == datetime(2024, 1, 15, 10, 30, 0)
    assert result.tzinfo is None


def test_date_only_no_time():
    """Date-only ISO string (no time component) should produce a naive date at midnight."""
    result = dt_from_iso("2024-01-15")
    assert result == datetime(2024, 1, 15, 0, 0, 0)
    assert result.tzinfo is None


def test_invalid_string_raises_value_error():
    """Non-ISO strings should raise ValueError containing the bad input."""
    with pytest.raises(ValueError, match="not-a-date"):
        dt_from_iso("not-a-date")
