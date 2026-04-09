from dataclasses import dataclass


@dataclass(slots=True)
class CameraSource:
    camera_id: str
    stream_url: str


def discover_cameras() -> list[CameraSource]:
    """Placeholder camera discovery implementation."""
    return []
