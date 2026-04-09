"""FastAPI route definitions for the Louisiana Live Traffic Model API."""

from fastapi import APIRouter, HTTPException, Query

from la_traffic.models import database as db
from la_traffic.models.schemas import TrafficCount

router = APIRouter(tags=["traffic"])


@router.get("/traffic/latest", response_model=list[TrafficCount])
def get_latest_traffic(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[TrafficCount]:
    """Return the most recent traffic observations across all cameras."""
    return db.get_latest_counts(limit=limit)


@router.get("/traffic/camera/{camera_id}", response_model=list[TrafficCount])
def get_camera_traffic(
    camera_id: str,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[TrafficCount]:
    """Return recent traffic observations for a single camera."""
    counts = db.get_counts_for_camera(camera_id, limit=limit)
    if not counts:
        raise HTTPException(
            status_code=404,
            detail=f"No traffic data found for camera '{camera_id}'.",
        )
    return counts
