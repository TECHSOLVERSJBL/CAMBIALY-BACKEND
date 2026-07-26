from datetime import datetime, timezone


def datetime_to_unix(dt: datetime) -> int:
    """Convierte un datetime de Python a Unix timestamp (segundos)."""
    return int(dt.replace(tzinfo=timezone.utc).timestamp())
