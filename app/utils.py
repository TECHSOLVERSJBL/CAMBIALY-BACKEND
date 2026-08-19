from datetime import datetime, timezone


def datetime_to_unix(dt: datetime) -> float:
    """Convierte un datetime de Python a Unix timestamp (float con precisión de microsegundos)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()
