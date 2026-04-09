"""511la.org camera discovery and source definitions."""

import logging
from dataclasses import dataclass, field

import requests

from la_traffic.config import settings

logger = logging.getLogger(__name__)

# Known 511la.org camera for single-camera development/testing.
# Camera at I-10 / Causeway Blvd interchange in Metairie.
# Snapshot URL format discovered by inspecting 511la.org network traffic.
_FALLBACK_CAMERA = {
    "camera_id": "LA-I10-CAUSEWAY",
    "name": "I-10 @ Causeway Blvd (Metairie)",
    "snapshot_url": "",  # populated from env or left blank — user must supply
    "stream_url": "",
    "latitude": 29.9929,
    "longitude": -90.1621,
    "highway": "I-10",
}


@dataclass(slots=True)
class CameraSource:
    camera_id: str
    name: str
    snapshot_url: str
    stream_url: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    highway: str = ""


def discover_cameras() -> list[CameraSource]:
    """Fetch camera list from 511la.org public API.

    The 511la.org system uses the Iteris SfT platform.
    Endpoint: GET /api/v2/get/cameras[?key=<key>]
    Returns JSON array of camera objects.
    """
    url = f"{settings.api_511la_base_url}/get/cameras"
    params: dict[str, str] = {}
    if settings.api_511la_key:
        params["key"] = settings.api_511la_key

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # API may return a top-level list or {"cameras": [...]}
        raw: list[dict] = data if isinstance(data, list) else data.get("cameras", [])

        cameras: list[CameraSource] = []
        for cam in raw:
            snapshot = cam.get("ImageUrl") or cam.get("imageUrl") or cam.get("image_url", "")
            stream = cam.get("VideoUrl") or cam.get("videoUrl") or cam.get("video_url", "")
            cameras.append(
                CameraSource(
                    camera_id=str(cam.get("ID") or cam.get("id") or ""),
                    name=str(cam.get("Name") or cam.get("name") or ""),
                    snapshot_url=snapshot,
                    stream_url=stream,
                    latitude=float(cam.get("Latitude") or cam.get("latitude") or 0),
                    longitude=float(cam.get("Longitude") or cam.get("longitude") or 0),
                )
            )

        logger.info("Discovered %d cameras from 511la.org", len(cameras))
        return cameras

    except Exception as exc:
        logger.warning("511la.org camera discovery failed: %s", exc)
        return []


def get_target_camera() -> CameraSource:
    """Return the camera to process.

    Resolution order:
    1. CAMERA_SNAPSHOT_URL env var (direct override, fastest for dev)
    2. CAMERA_ID env var → search discovered camera list
    3. First camera returned by the API
    4. Fallback stub (snapshot_url will be empty — pipeline will error clearly)
    """
    # Direct URL override
    if settings.camera_snapshot_url:
        cam_id = settings.camera_id or _FALLBACK_CAMERA["camera_id"]
        logger.info("Using camera snapshot URL from env: %s", settings.camera_snapshot_url)
        return CameraSource(
            camera_id=cam_id,
            name=f"Camera {cam_id}",
            snapshot_url=settings.camera_snapshot_url,
        )

    # Try API
    cameras = discover_cameras()

    if cameras:
        if settings.camera_id:
            for cam in cameras:
                if cam.camera_id == settings.camera_id:
                    logger.info("Found camera %s: %s", cam.camera_id, cam.name)
                    return cam
            logger.warning(
                "Camera ID %r not found in API results, using first available.",
                settings.camera_id,
            )
        logger.info("Using first discovered camera: %s", cameras[0].name)
        return cameras[0]

    # Fallback stub
    logger.warning(
        "No cameras discovered. Set CAMERA_SNAPSHOT_URL in .env to run the pipeline."
    )
    fb = _FALLBACK_CAMERA
    return CameraSource(
        camera_id=fb["camera_id"],
        name=fb["name"],
        snapshot_url=fb["snapshot_url"],
        latitude=fb["latitude"],
        longitude=fb["longitude"],
        highway=fb["highway"],
    )
