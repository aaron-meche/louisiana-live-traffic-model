"""YOLOv8 vehicle detection using Ultralytics + Supervision."""

import logging

import numpy as np
import supervision as sv
from ultralytics import YOLO

from la_traffic.config import settings

logger = logging.getLogger(__name__)

# COCO class IDs that are vehicles (the only ones we care about).
VEHICLE_CLASS_IDS: set[int] = {
    2,   # car
    3,   # motorcycle
    5,   # bus
    7,   # truck
}


class VehicleDetector:
    """Loads a YOLOv8 model and runs vehicle-only detection on frames.

    The model is loaded once at construction and reused across frames.
    Only detections whose class_id is in VEHICLE_CLASS_IDS are returned.
    """

    def __init__(
        self,
        model_path: str | None = None,
        confidence: float | None = None,
    ) -> None:
        model_path = model_path or settings.yolo_model
        confidence = confidence if confidence is not None else settings.confidence_threshold

        logger.info("Loading YOLO model: %s", model_path)
        self._model = YOLO(model_path)
        self._confidence = confidence
        logger.info("YOLO model loaded (conf=%.2f)", confidence)

    def detect(self, frame: np.ndarray) -> sv.Detections:
        """Run inference on a single BGR frame.

        Args:
            frame: OpenCV BGR image (H, W, 3).

        Returns:
            sv.Detections containing only vehicle-class detections.
        """
        results = self._model.predict(
            source=frame,
            conf=self._confidence,
            verbose=False,
        )[0]

        detections = sv.Detections.from_ultralytics(results)

        # Filter to vehicle classes only
        if detections.class_id is not None and len(detections) > 0:
            vehicle_mask = np.isin(detections.class_id, list(VEHICLE_CLASS_IDS))
            detections = detections[vehicle_mask]

        logger.debug("Detected %d vehicles in frame", len(detections))
        return detections
