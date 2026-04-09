from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DensityLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CONGESTED = "CONGESTED"


class TrafficCount(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    camera_id: str
    timestamp: datetime
    interval_sec: int
    total_vehicles: int
    cars: int = 0
    suvs: int = 0
    trucks: int = 0
    heavy_vehicles: int = 0
    avg_speed_est: float | None = None
    density_level: DensityLevel = DensityLevel.LOW
