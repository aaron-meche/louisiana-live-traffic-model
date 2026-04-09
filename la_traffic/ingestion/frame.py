"""Frame acquisition from camera snapshot URLs and RTSP/HLS streams."""

import logging

import cv2
import numpy as np
import requests

logger = logging.getLogger(__name__)

# Requests session with a browser-like User-Agent so DOT servers don't reject us.
_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (compatible; LA-Traffic-Model/0.1; "
            "+https://github.com/user/louisiana-live-traffic-model)"
        )
    }
)


def fetch_snapshot(snapshot_url: str, timeout: int = 10) -> np.ndarray | None:
    """Download a JPEG/PNG snapshot and decode it to an OpenCV BGR frame.

    Args:
        snapshot_url: HTTP(S) URL that returns a JPEG or PNG image.
        timeout: Request timeout in seconds.

    Returns:
        BGR numpy array (H, W, 3) or None on failure.
    """
    try:
        resp = _session.get(snapshot_url, timeout=timeout)
        resp.raise_for_status()

        img_array = np.frombuffer(resp.content, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if frame is None:
            logger.warning("imdecode returned None for URL: %s", snapshot_url)
            return None

        logger.debug("Fetched frame %dx%d from %s", frame.shape[1], frame.shape[0], snapshot_url)
        return frame

    except requests.RequestException as exc:
        logger.warning("HTTP error fetching snapshot from %s: %s", snapshot_url, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error fetching snapshot: %s", exc)
        return None


class StreamCapture:
    """Thin wrapper around cv2.VideoCapture for RTSP/HLS streams."""

    def __init__(self, stream_url: str) -> None:
        self._url = stream_url
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self._url)
        if not self._cap.isOpened():
            logger.warning("Could not open stream: %s", self._url)
            return False
        logger.info("Opened stream: %s", self._url)
        return True

    def read(self) -> np.ndarray | None:
        if self._cap is None or not self._cap.isOpened():
            return None
        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "StreamCapture":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.release()
