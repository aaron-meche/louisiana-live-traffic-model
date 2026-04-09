from fastapi import APIRouter

from la_traffic.models.schemas import TrafficCount

router = APIRouter(tags=["traffic"])


@router.get("/traffic/latest", response_model=list[TrafficCount])
def get_latest_traffic() -> list[TrafficCount]:
    """Return latest traffic observations."""
    return []
