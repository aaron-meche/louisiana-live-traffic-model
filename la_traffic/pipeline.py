"""Single-camera traffic analysis pipeline.

Runs a continuous loop that:
1. Fetches JPEG snapshots from the target camera at a configurable interval.
2. Runs YOLOv8 vehicle detection on each frame.
3. Tracks vehicles across frames with ByteTrack and counts line crossings.
4. Classifies each detected vehicle (car / truck / heavy / motorcycle).
5. At the end of each counting window, persists a TrafficCount record.

Usage:
    python run_pipeline.py                      # uses .env config
    python run_pipeline.py --window 30          # 30-second windows
    python run_pipeline.py --no-db              # print only, skip DB
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import numpy as np

from la_traffic.config import settings
from la_traffic.detection.classifier import VehicleType, classify_detections, tally_types
from la_traffic.detection.detector import VehicleDetector
from la_traffic.detection.tracker import VehicleCounter
from la_traffic.ingestion.camera import CameraSource, get_target_camera
from la_traffic.ingestion.frame import fetch_snapshot
from la_traffic.models.schemas import DensityLevel, TrafficCount

logger = logging.getLogger(__name__)


# ── Density thresholds (vehicles per minute) ─────────────────────────────────
# Rough heuristics for a single highway camera — can be tuned later.
def compute_density(vehicles_per_minute: float) -> DensityLevel:
    if vehicles_per_minute < 10:
        return DensityLevel.LOW
    if vehicles_per_minute < 30:
        return DensityLevel.MODERATE
    if vehicles_per_minute < 60:
        return DensityLevel.HIGH
    return DensityLevel.CONGESTED


# ── Per-window state ──────────────────────────────────────────────────────────

class WindowAccumulator:
    """Accumulates per-frame classification counts over one counting window."""

    def __init__(self) -> None:
        self.cars = 0
        self.motorcycles = 0
        self.trucks = 0
        self.heavy_vehicles = 0
        self.frames_processed = 0

    def add_frame_classifications(self, cars: int, motorcycles: int, trucks: int, heavy: int) -> None:
        # We track peak counts per frame rather than cumulative detections
        # to avoid inflating counts when the same vehicle appears in many frames.
        # Peak-per-frame is an approximation until line-crossing is reliable.
        self.cars = max(self.cars, cars)
        self.motorcycles = max(self.motorcycles, motorcycles)
        self.trucks = max(self.trucks, trucks)
        self.heavy_vehicles = max(self.heavy_vehicles, heavy)
        self.frames_processed += 1

    @property
    def total(self) -> int:
        return self.cars + self.motorcycles + self.trucks + self.heavy_vehicles


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(
    camera: CameraSource | None = None,
    window_sec: int | None = None,
    save_to_db: bool = True,
    max_windows: int | None = None,
) -> None:
    """Run the single-camera pipeline indefinitely (or for max_windows windows).

    Args:
        camera: Camera to process. Defaults to get_target_camera().
        window_sec: Length of each counting window in seconds.
        save_to_db: Whether to persist results to the database.
        max_windows: Stop after this many windows (None = run forever).
    """
    if camera is None:
        camera = get_target_camera()

    if not camera.snapshot_url:
        raise ValueError(
            f"Camera {camera.camera_id!r} has no snapshot URL. "
            "Set CAMERA_SNAPSHOT_URL in your .env file."
        )

    window_sec = window_sec or settings.pipeline_window_sec
    interval = settings.snapshot_interval_sec

    logger.info(
        "Starting pipeline for camera=%s (%s)",
        camera.camera_id,
        camera.name,
    )
    logger.info(
        "Window=%ds  interval=%.1fs  save_db=%s",
        window_sec,
        interval,
        save_to_db,
    )

    # Load YOLO model once
    detector = VehicleDetector()

    # Fetch first frame to get dimensions for the tracker
    logger.info("Fetching initial frame to determine dimensions…")
    first_frame = _wait_for_frame(camera.snapshot_url, max_retries=5)
    if first_frame is None:
        raise RuntimeError(
            f"Could not fetch a valid frame from {camera.snapshot_url}. "
            "Check the URL and your internet connection."
        )

    h, w = first_frame.shape[:2]
    logger.info("Frame dimensions: %dx%d", w, h)

    counter = VehicleCounter(frame_width=w, frame_height=h)

    windows_done = 0

    while max_windows is None or windows_done < max_windows:
        accumulator = WindowAccumulator()
        window_start = time.monotonic()
        frame = first_frame if windows_done == 0 else None

        # ── Inner frame loop ──────────────────────────────────────────────
        while time.monotonic() - window_start < window_sec:
            if frame is None:
                frame = fetch_snapshot(camera.snapshot_url)

            if frame is not None:
                _process_frame(frame, detector, counter, accumulator, w, h)

            frame = None  # fetch fresh next iteration
            time.sleep(interval)
        # ─────────────────────────────────────────────────────────────────

        window_counts = counter.flush_window()

        # Use crossing counts if available, fall back to peak instantaneous
        total_vehicles = window_counts.total_crossings or accumulator.total
        elapsed_min = window_sec / 60.0
        vpm = total_vehicles / elapsed_min if elapsed_min > 0 else 0
        density = compute_density(vpm)

        record = TrafficCount(
            camera_id=camera.camera_id,
            timestamp=datetime.now(tz=timezone.utc).replace(tzinfo=None),
            interval_sec=window_sec,
            total_vehicles=total_vehicles,
            cars=accumulator.cars,
            trucks=accumulator.trucks,
            heavy_vehicles=accumulator.heavy_vehicles,
            density_level=density,
        )

        _report(record, window_counts, accumulator)

        if save_to_db:
            from la_traffic.models.database import save_traffic_count
            save_traffic_count(record)

        windows_done += 1


def _process_frame(
    frame: np.ndarray,
    detector: VehicleDetector,
    counter: VehicleCounter,
    accumulator: WindowAccumulator,
    frame_width: int,
    frame_height: int,
) -> None:
    detections = detector.detect(frame)
    counter.update(detections)

    if len(detections) > 0 and detections.class_id is not None:
        classifications = classify_detections(
            detections.class_id,
            bboxes_xyxy=detections.xyxy,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        tally = tally_types(classifications)
        accumulator.add_frame_classifications(
            cars=tally["cars"],
            motorcycles=tally["motorcycles"],
            trucks=tally["trucks"],
            heavy=tally["heavy_vehicles"],
        )


def _wait_for_frame(url: str, max_retries: int = 5) -> np.ndarray | None:
    """Retry fetching a frame with exponential backoff."""
    for attempt in range(max_retries):
        frame = fetch_snapshot(url)
        if frame is not None:
            return frame
        wait = 2 ** attempt
        logger.warning("Frame fetch attempt %d/%d failed, retrying in %ds…", attempt + 1, max_retries, wait)
        time.sleep(wait)
    return None


def _report(record: TrafficCount, window_counts, accumulator: WindowAccumulator) -> None:
    print(
        f"\n[{record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
        f"Camera: {record.camera_id}"
    )
    print(f"  Window:        {record.interval_sec}s")
    print(f"  Total vehicles: {record.total_vehicles}  ({record.density_level.value})")
    print(f"  Line crossings: in={window_counts.direction_in}  out={window_counts.direction_out}")
    print(f"  Peak frame:    {window_counts.peak_instantaneous} visible at once")
    print(f"  Cars:          {record.cars}")
    print(f"  Trucks:        {record.trucks}")
    print(f"  Heavy (18w+):  {record.heavy_vehicles}")
    print(f"  Frames processed: {accumulator.frames_processed}")
