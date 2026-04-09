import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    # Server
    app_env: str = os.getenv("APP_ENV", "development")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://la_traffic:la_traffic@localhost:5432/la_traffic",
    )

    # 511la.org API
    api_511la_key: str = os.getenv("API_511LA_KEY", "")
    api_511la_base_url: str = os.getenv(
        "API_511LA_BASE_URL", "https://511la.org/api/v2"
    )

    # Single-camera override (set this in .env to skip API discovery)
    camera_id: str = os.getenv("CAMERA_ID", "")
    camera_snapshot_url: str = os.getenv("CAMERA_SNAPSHOT_URL", "")

    # YOLOv8
    yolo_model: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))

    # Pipeline timing
    snapshot_interval_sec: float = float(os.getenv("SNAPSHOT_INTERVAL_SEC", "2.0"))
    pipeline_window_sec: int = int(os.getenv("PIPELINE_WINDOW_SEC", "60"))


settings = Settings()
