"""Vehicle tracking and line-crossing counting via Supervision + ByteTrack.

The counting line is drawn horizontally across the vertical center of the frame.
Vehicles crossing downward (in_count) and upward (out_count) are tracked
independently, giving a rough proxy for two directions of traffic.

Note: Line-crossing tracking requires temporal continuity between frames.
It works best with live RTSP/HLS streams. When using periodic JPEG snapshots
the ByteTracker may lose tracks between frames, so the pipeline also maintains
a per-window peak-count as a fallback density metric.
"""

import logging
from dataclasses import dataclass, field

import numpy as np
import supervision as sv

logger = logging.getLogger(__name__)


@dataclass
class CrossingEvent:
    """One vehicle crossing the counting line."""
    track_id: int
    class_id: int
    direction: str  # "in" (top→bottom) or "out" (bottom→top)


@dataclass
class FrameResult:
    """Results from processing a single frame."""
    crossings: list[CrossingEvent] = field(default_factory=list)
    instantaneous_count: int = 0  # vehicles visible right now


@dataclass
class WindowCounts:
    """Accumulated counts over a pipeline window."""
    direction_in: int = 0    # crossed top→bottom
    direction_out: int = 0   # crossed bottom→top
    peak_instantaneous: int = 0

    @property
    def total_crossings(self) -> int:
        return self.direction_in + self.direction_out


class VehicleCounter:
    """Stateful per-camera vehicle counter.

    One instance per camera session. Maintains ByteTracker state and
    LineZone crossing counts across successive frames.
    """

    def __init__(self, frame_width: int, frame_height: int) -> None:
        self._width = frame_width
        self._height = frame_height

        # Horizontal counting line at the vertical center
        line_y = frame_height // 2
        self._line_zone = sv.LineZone(
            start=sv.Point(0, line_y),
            end=sv.Point(frame_width, line_y),
        )

        self._tracker = sv.ByteTrack()
        self._window = WindowCounts()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: sv.Detections) -> FrameResult:
        """Feed new detections from one frame into the tracker.

        Args:
            detections: Vehicle detections from VehicleDetector.detect().

        Returns:
            FrameResult with crossing events and instantaneous vehicle count.
        """
        result = FrameResult(instantaneous_count=len(detections))

        if len(detections) == 0:
            self._window.peak_instantaneous = max(
                self._window.peak_instantaneous, 0
            )
            return result

        # Update ByteTracker — assigns/maintains track IDs
        tracked = self._tracker.update_with_detections(detections)

        # Check line crossings
        crossed_in_mask, crossed_out_mask = self._line_zone.trigger(tracked)

        for idx in np.where(crossed_in_mask)[0]:
            tid = int(tracked.tracker_id[idx]) if tracked.tracker_id is not None else -1
            cid = int(tracked.class_id[idx]) if tracked.class_id is not None else -1
            result.crossings.append(CrossingEvent(tid, cid, "in"))
            self._window.direction_in += 1

        for idx in np.where(crossed_out_mask)[0]:
            tid = int(tracked.tracker_id[idx]) if tracked.tracker_id is not None else -1
            cid = int(tracked.class_id[idx]) if tracked.class_id is not None else -1
            result.crossings.append(CrossingEvent(tid, cid, "out"))
            self._window.direction_out += 1

        self._window.peak_instantaneous = max(
            self._window.peak_instantaneous, len(tracked)
        )

        if result.crossings:
            logger.debug(
                "%d crossing(s) this frame — running totals: in=%d out=%d",
                len(result.crossings),
                self._window.direction_in,
                self._window.direction_out,
            )

        return result

    def flush_window(self) -> WindowCounts:
        """Return accumulated window counts and reset for the next window."""
        counts = WindowCounts(
            direction_in=self._window.direction_in,
            direction_out=self._window.direction_out,
            peak_instantaneous=self._window.peak_instantaneous,
        )
        self._window = WindowCounts()
        return counts

    @property
    def line_y(self) -> int:
        return self._height // 2
