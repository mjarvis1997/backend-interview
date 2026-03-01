"""Unit tests for generate_cache_key in dependencies/redis.py.

generate_cache_key is a pure function — no Redis connection is needed.
"""
import hashlib

from app.dependencies.redis import generate_cache_key


# ---------------------------------------------------------------------------
# Helper — replicates the production algorithm so expected values are
# derived from the same logic rather than hardcoded magic strings.
# ---------------------------------------------------------------------------

def expected_key(*args) -> str:
    key_string = "|".join(str(a) for a in args if a is not None)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"events:stats:{key_hash}"


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

def test_key_has_correct_prefix():
    key = generate_cache_key("a")
    assert key.startswith("events:stats:")


def test_key_suffix_is_32_char_hex():
    """MD5 digest should be a 32-character hex string."""
    key = generate_cache_key("a")
    suffix = key.removeprefix("events:stats:")
    assert len(suffix) == 32
    assert all(c in "0123456789abcdef" for c in suffix)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_args_produce_same_key():
    assert generate_cache_key("daily", "2024-01") == generate_cache_key("daily", "2024-01")


def test_different_args_produce_different_keys():
    assert generate_cache_key("daily") != generate_cache_key("weekly")


def test_arg_order_affects_key():
    """Argument order must change the key — not commutative."""
    assert generate_cache_key("a", "b") != generate_cache_key("b", "a")


# ---------------------------------------------------------------------------
# None filtering
# ---------------------------------------------------------------------------

def test_none_args_are_excluded():
    """None values should be dropped; generate_cache_key('a', None) == generate_cache_key('a')."""
    assert generate_cache_key("a", None) == generate_cache_key("a")


def test_none_between_values_is_excluded():
    """None in the middle should be dropped, not treated as an empty segment."""
    assert generate_cache_key("a", None, "b") == generate_cache_key("a", "b")


def test_all_none_args_produces_a_key():
    """All-None input produces a valid (empty-string) key rather than raising."""
    key = generate_cache_key(None, None)
    assert key.startswith("events:stats:")


# ---------------------------------------------------------------------------
# Value matches expected algorithm
# ---------------------------------------------------------------------------

def test_output_matches_expected_algorithm():
    """Spot-check that the full output matches a local reimplementation."""
    assert generate_cache_key("realtime-stats") == expected_key("realtime-stats")


def test_multi_arg_output_matches_expected_algorithm():
    assert generate_cache_key("daily", "2024-01-01", None, "user-1") == expected_key("daily", "2024-01-01", None, "user-1")
