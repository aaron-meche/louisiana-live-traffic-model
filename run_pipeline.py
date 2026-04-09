#!/usr/bin/env python3
"""Entry point for the single-camera traffic analysis pipeline.

Examples:
    # Run with settings from .env (default 60-second windows, save to DB)
    python run_pipeline.py

    # 30-second windows, no database
    python run_pipeline.py --window 30 --no-db

    # Override camera snapshot URL on the command line
    python run_pipeline.py --snapshot-url "https://example.com/camera.jpg"

    # Run exactly 5 windows then exit (useful for testing)
    python run_pipeline.py --windows 5 --no-db
"""

import argparse
import logging
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Louisiana Live Traffic Model — single-camera pipeline"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Length of each counting window in seconds (default: PIPELINE_WINDOW_SEC from .env or 60).",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Print results to stdout only; do not write to the database.",
    )
    parser.add_argument(
        "--windows",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N windows (default: run forever).",
    )
    parser.add_argument(
        "--snapshot-url",
        default=None,
        metavar="URL",
        help="Camera JPEG snapshot URL (overrides CAMERA_SNAPSHOT_URL in .env).",
    )
    parser.add_argument(
        "--camera-id",
        default=None,
        metavar="ID",
        help="Camera ID used for DB records (overrides CAMERA_ID in .env).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Apply CLI overrides before importing pipeline (config is read at import time)
    import os
    if args.snapshot_url:
        os.environ["CAMERA_SNAPSHOT_URL"] = args.snapshot_url
    if args.camera_id:
        os.environ["CAMERA_ID"] = args.camera_id

    # Late imports so env overrides are in place before config.py reads them
    from la_traffic.ingestion.camera import get_target_camera
    from la_traffic.models.database import create_tables
    from la_traffic.pipeline import run_pipeline

    save_to_db = not args.no_db

    if save_to_db:
        ok = create_tables()
        if not ok:
            print(
                "WARNING: Database not available. Continuing without saving. "
                "Use --no-db to suppress this warning.",
                file=sys.stderr,
            )
            save_to_db = False

    camera = get_target_camera()
    print(f"Target camera: [{camera.camera_id}] {camera.name}")
    print(f"Snapshot URL:  {camera.snapshot_url or '(not set)'}")

    if not camera.snapshot_url:
        print(
            "\nERROR: No camera snapshot URL configured.\n"
            "Set CAMERA_SNAPSHOT_URL in your .env file or pass --snapshot-url.\n"
            "\nExample .env entry:\n"
            "  CAMERA_SNAPSHOT_URL=https://example.com/cameras/i10-causeway.jpg\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        run_pipeline(
            camera=camera,
            window_sec=args.window,
            save_to_db=save_to_db,
            max_windows=args.windows,
        )
    except KeyboardInterrupt:
        print("\nPipeline stopped by user.")


if __name__ == "__main__":
    main()
