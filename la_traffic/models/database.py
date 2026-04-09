"""SQLAlchemy ORM table definition and database helpers.

Uses TimescaleDB (PostgreSQL extension) for the traffic_counts table.
The hypertable is created automatically on first startup if the database
is available. All DB operations degrade gracefully if the DB is not reachable.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

from la_traffic.config import settings
from la_traffic.models.schemas import DensityLevel, TrafficCount

logger = logging.getLogger(__name__)


# ── ORM base ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class TrafficCountRow(Base):
    """ORM model matching the TrafficCount Pydantic schema."""

    __tablename__ = "traffic_counts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=False), nullable=False, index=True)
    interval_sec = Column(Integer, nullable=False)
    total_vehicles = Column(Integer, nullable=False, default=0)
    cars = Column(Integer, nullable=False, default=0)
    motorcycles = Column(Integer, nullable=False, default=0)
    trucks = Column(Integer, nullable=False, default=0)
    heavy_vehicles = Column(Integer, nullable=False, default=0)
    avg_speed_est = Column(Float, nullable=True)
    density_level = Column(String(16), nullable=False, default="LOW")


# ── Engine singleton ────────────────────────────────────────────────────────

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


# ── Setup ───────────────────────────────────────────────────────────────────

def create_tables() -> bool:
    """Create tables and attempt to convert to TimescaleDB hypertable.

    Returns True on success, False if DB is unavailable.
    """
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        logger.info("Database tables created / verified.")

        # Convert to hypertable (idempotent — fails silently if already done)
        with engine.connect() as conn:
            try:
                conn.execute(
                    text(
                        "SELECT create_hypertable('traffic_counts', 'timestamp', "
                        "if_not_exists => TRUE);"
                    )
                )
                conn.commit()
                logger.info("TimescaleDB hypertable configured.")
            except Exception as exc:
                # TimescaleDB extension might not be installed (plain PG is fine)
                logger.debug("Hypertable creation skipped: %s", exc)
                conn.rollback()

        return True

    except Exception as exc:
        logger.warning("Database setup failed (DB may not be running): %s", exc)
        return False


# ── Write ────────────────────────────────────────────────────────────────────

def save_traffic_count(count: TrafficCount) -> bool:
    """Persist a TrafficCount record. Returns True on success."""
    try:
        engine = get_engine()
        row = TrafficCountRow(
            id=count.id,
            camera_id=count.camera_id,
            timestamp=count.timestamp,
            interval_sec=count.interval_sec,
            total_vehicles=count.total_vehicles,
            cars=count.cars,
            motorcycles=getattr(count, "motorcycles", 0),
            trucks=count.trucks,
            heavy_vehicles=count.heavy_vehicles,
            avg_speed_est=count.avg_speed_est,
            density_level=count.density_level.value,
        )
        with Session(engine) as session:
            session.add(row)
            session.commit()
        logger.info(
            "Saved traffic count for camera=%s total=%d density=%s",
            count.camera_id,
            count.total_vehicles,
            count.density_level.value,
        )
        return True

    except Exception as exc:
        logger.warning("Failed to save traffic count to DB: %s", exc)
        return False


# ── Read ─────────────────────────────────────────────────────────────────────

def get_latest_counts(limit: int = 50) -> list[TrafficCount]:
    """Return the most recent traffic counts across all cameras."""
    try:
        engine = get_engine()
        with Session(engine) as session:
            rows = (
                session.query(TrafficCountRow)
                .order_by(TrafficCountRow.timestamp.desc())
                .limit(limit)
                .all()
            )
        return [_row_to_schema(r) for r in rows]
    except Exception as exc:
        logger.warning("Failed to query traffic counts: %s", exc)
        return []


def get_counts_for_camera(camera_id: str, limit: int = 50) -> list[TrafficCount]:
    """Return recent counts for a specific camera."""
    try:
        engine = get_engine()
        with Session(engine) as session:
            rows = (
                session.query(TrafficCountRow)
                .filter(TrafficCountRow.camera_id == camera_id)
                .order_by(TrafficCountRow.timestamp.desc())
                .limit(limit)
                .all()
            )
        return [_row_to_schema(r) for r in rows]
    except Exception as exc:
        logger.warning("Failed to query counts for camera %s: %s", camera_id, exc)
        return []


def _row_to_schema(row: TrafficCountRow) -> TrafficCount:
    return TrafficCount(
        id=row.id,
        camera_id=row.camera_id,
        timestamp=row.timestamp,
        interval_sec=row.interval_sec,
        total_vehicles=row.total_vehicles,
        cars=row.cars,
        trucks=row.trucks,
        heavy_vehicles=row.heavy_vehicles,
        avg_speed_est=row.avg_speed_est,
        density_level=DensityLevel(row.density_level),
    )
