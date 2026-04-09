from collections.abc import Iterable
from typing import Any


def count_vehicles(detections: Iterable[dict[str, Any]]) -> int:
    """Placeholder vehicle counting implementation."""
    return len(list(detections))
