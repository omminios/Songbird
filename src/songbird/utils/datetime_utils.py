"""
DateTime utility functions for Songbird
Consistent datetime handling across the application
"""
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """
    Get current UTC time as ISO 8601 string

    Returns:
        str: Current UTC time in ISO 8601 format (e.g., "2025-01-15T10:30:45.123456+00:00")

    Example:
        >>> timestamp = utc_now_iso()
        >>> print(timestamp)
        '2025-01-15T10:30:45.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


def format_timestamp(timestamp: float) -> str:
    """
    Convert Unix timestamp to human-readable UTC format

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        str: Formatted datetime string (e.g., "2025-01-15 10:30:45")

    Example:
        >>> import time
        >>> ts = time.time()
        >>> formatted = format_timestamp(ts)
        >>> print(formatted)
        '2025-01-15 10:30:45'
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
