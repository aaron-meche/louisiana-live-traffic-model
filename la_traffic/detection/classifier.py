"""Vehicle type and weight classification from COCO class IDs.

YOLO models trained on COCO use these class IDs for vehicles:
  2  → car        (sedans, coupes, hatchbacks, crossovers)
  3  → motorcycle
  5  → bus        (transit buses, school buses, coach)
  7  → truck      (pickup trucks, delivery vans, 18-wheelers)

COCO's "truck" class is broad — it covers everything from F-150s to semi
trucks. We add a second heuristic pass using bounding-box aspect ratio and
area to split "truck" into pickup/light-truck vs heavy/18-wheeler.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class VehicleType(str, Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    TRUCK = "truck"
    HEAVY = "heavy"   # 18-wheelers, large buses, semis
    UNKNOWN = "unknown"


class WeightClass(str, Enum):
    LIGHT = "light"       # < ~5,500 lbs  (cars, motorcycles, pickups)
    MEDIUM = "medium"     # 5,500–26,000 lbs (delivery vans, small trucks)
    HEAVY = "heavy"       # > 26,000 lbs  (semis, large buses)


@dataclass(frozen=True)
class VehicleClassification:
    vehicle_type: VehicleType
    weight_class: WeightClass


# ── COCO ID → base type ────────────────────────────────────────────────────
_COCO_TO_BASE: dict[int, VehicleType] = {
    2: VehicleType.CAR,
    3: VehicleType.MOTORCYCLE,
    5: VehicleType.HEAVY,   # bus → heavy by default
    7: VehicleType.TRUCK,   # truck (may be refined below)
}

_TYPE_TO_WEIGHT: dict[VehicleType, WeightClass] = {
    VehicleType.CAR: WeightClass.LIGHT,
    VehicleType.MOTORCYCLE: WeightClass.LIGHT,
    VehicleType.TRUCK: WeightClass.MEDIUM,
    VehicleType.HEAVY: WeightClass.HEAVY,
    VehicleType.UNKNOWN: WeightClass.LIGHT,
}

# Fraction of frame area at which a "truck" detection is likely a semi/heavy.
# An 18-wheeler at reasonable distance occupies ~8%+ of a typical camera frame.
_HEAVY_AREA_FRACTION = 0.08


def classify_detection(
    class_id: int,
    bbox_xyxy: np.ndarray | None = None,
    frame_width: int = 1,
    frame_height: int = 1,
) -> VehicleClassification:
    """Classify a single detection into VehicleType + WeightClass.

    Args:
        class_id: COCO class ID from YOLO output.
        bbox_xyxy: [x1, y1, x2, y2] bounding box (optional, used for heavy heuristic).
        frame_width: Frame width in pixels (used to compute area fraction).
        frame_height: Frame height in pixels.

    Returns:
        VehicleClassification with type and estimated weight class.
    """
    base_type = _COCO_TO_BASE.get(class_id, VehicleType.UNKNOWN)

    # Refine COCO "truck" using bounding box size when available
    if base_type == VehicleType.TRUCK and bbox_xyxy is not None:
        x1, y1, x2, y2 = bbox_xyxy
        bbox_area = (x2 - x1) * (y2 - y1)
        frame_area = frame_width * frame_height
        if frame_area > 0 and (bbox_area / frame_area) >= _HEAVY_AREA_FRACTION:
            base_type = VehicleType.HEAVY

    return VehicleClassification(
        vehicle_type=base_type,
        weight_class=_TYPE_TO_WEIGHT[base_type],
    )


def classify_detections(
    class_ids: np.ndarray,
    bboxes_xyxy: np.ndarray | None = None,
    frame_width: int = 1,
    frame_height: int = 1,
) -> list[VehicleClassification]:
    """Classify a batch of detections.

    Args:
        class_ids: Array of COCO class IDs, shape (N,).
        bboxes_xyxy: Array of bounding boxes, shape (N, 4), or None.
        frame_width: Frame width for heavy-vehicle heuristic.
        frame_height: Frame height for heavy-vehicle heuristic.

    Returns:
        List of VehicleClassification, one per detection.
    """
    results: list[VehicleClassification] = []
    for i, cid in enumerate(class_ids):
        bbox = bboxes_xyxy[i] if bboxes_xyxy is not None and i < len(bboxes_xyxy) else None
        results.append(classify_detection(int(cid), bbox, frame_width, frame_height))
    return results


def tally_types(classifications: list[VehicleClassification]) -> dict[str, int]:
    """Count vehicles by type from a list of classifications.

    Returns dict with keys: cars, motorcycles, trucks, heavy_vehicles.
    """
    tally: dict[str, int] = {"cars": 0, "motorcycles": 0, "trucks": 0, "heavy_vehicles": 0}
    _type_key = {
        VehicleType.CAR: "cars",
        VehicleType.MOTORCYCLE: "motorcycles",
        VehicleType.TRUCK: "trucks",
        VehicleType.HEAVY: "heavy_vehicles",
    }
    for clf in classifications:
        key = _type_key.get(clf.vehicle_type)
        if key:
            tally[key] += 1
    return tally
