from datetime import datetime


def dt_from_iso(iso_str: str):
    """Convert ISO 8601 string to datetime object, handling 'Z' for UTC."""
    try:
        return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 date format: {iso_str}") from e
