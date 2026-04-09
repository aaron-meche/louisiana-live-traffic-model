# Louisiana Live Traffic Model

**Real-time traffic analysis for Louisiana highways powered by computer vision.**

Louisiana Live Traffic Model ingests live camera feeds from [511la.org](https://www.511la.org), detects and classifies vehicles using YOLOv8, and visualizes traffic density on an interactive map with color-coded overlays.

---

## Features

- **Live Camera Ingestion** — Pulls RTSP/HLS streams from Louisiana's 511 traffic camera network covering I-10, I-20, I-49, I-210, and more.
- **Vehicle Detection & Counting** — Uses YOLOv8 with line-crossing logic to count vehicles per minute at each camera location.
- **Vehicle Classification** — Categorizes detected vehicles (car, SUV, truck, bus, 18-wheeler) with estimated weight class.
- **Traffic Density Map** — Interactive map overlay with color-coded segments (green → red) reflecting real-time traffic volume.
- **Historical Analytics** — Time-series data storage for trend analysis, peak-hour detection, and route comparison.
- **REST API** — Serves traffic data for downstream integrations and dashboards.

## Architecture

```
511la.org Cameras
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Ingestion  │────▶│  Detection   │────▶│   Database   │
│   Service    │     │  Pipeline    │     │  (Timescale) │
│  (FFmpeg +   │     │  (YOLOv8 +   │     │              │
│   OpenCV)    │     │  Supervision)│     └──────┬───────┘
└──────────────┘     └──────────────┘            │
                                                 ▼
                                          ┌──────────────┐
                                          │   REST API   │
                                          │  (FastAPI)   │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   Frontend   │
                                          │  (React +    │
                                          │   Mapbox)    │
                                          └──────────────┘
```

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Ingestion      | Python, FFmpeg, OpenCV              |
| Detection      | Ultralytics YOLOv8, Supervision     |
| Database       | PostgreSQL + TimescaleDB            |
| API            | FastAPI                             |
| Frontend       | React, Mapbox GL JS                 |
| Infrastructure | Docker, Docker Compose              |

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+
- Mapbox API key

## Project Structure

```
louisiana-live-traffic-model/
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── la_traffic/
│   ├── __init__.py
│   ├── main.py
│   ├── ingestion/          # Camera feed acquisition
│   │   ├── __init__.py
│   │   ├── camera.py       # Camera discovery & stream handling
│   │   └── frame.py        # Frame extraction & preprocessing
│   ├── detection/          # Vehicle detection & classification
│   │   ├── __init__.py
│   │   ├── detector.py     # YOLOv8 inference
│   │   ├── tracker.py      # Vehicle tracking & counting
│   │   └── classifier.py   # Vehicle type & weight estimation
│   ├── models/             # Data models & database
│   │   ├── __init__.py
│   │   ├── schemas.py      # Pydantic models
│   │   └── database.py     # TimescaleDB connection & queries
│   ├── api/                # REST API
│   │   ├── __init__.py
│   │   └── routes.py       # FastAPI endpoints
│   └── config.py           # App configuration
├── frontend/               # React map application
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── TrafficMap.jsx
│   │   │   └── CameraPanel.jsx
│   │   └── hooks/
│   │       └── useTrafficData.js
│   └── public/
└── tests/
    ├── test_ingestion.py
    ├── test_detection.py
    └── test_api.py
```

## Data Model

### TrafficCount

| Field            | Type      | Description                              |
|------------------|-----------|------------------------------------------|
| `id`             | UUID      | Primary key                              |
| `camera_id`      | String    | 511la.org camera identifier              |
| `timestamp`      | DateTime  | Observation time                         |
| `interval_sec`   | Integer   | Counting window duration                 |
| `total_vehicles` | Integer   | Total vehicles in interval               |
| `cars`           | Integer   | Sedans, coupes, hatchbacks               |
| `suvs`           | Integer   | SUVs, crossovers, minivans               |
| `trucks`         | Integer   | Pickup trucks                            |
| `heavy_vehicles` | Integer   | 18-wheelers, buses, large trucks         |
| `avg_speed_est`  | Float     | Estimated avg speed (if tracking allows) |
| `density_level`  | Enum      | LOW, MODERATE, HIGH, CONGESTED           |

## Roadmap

- [x] Project scaffolding & architecture design
- [ ] 511la.org API integration & camera discovery
- [ ] Frame extraction pipeline
- [ ] YOLOv8 vehicle detection baseline
- [ ] Line-crossing vehicle counter
- [ ] TimescaleDB schema & ingestion
- [ ] FastAPI traffic data endpoints
- [ ] React + Mapbox map overlay (green/yellow/red)
- [ ] Vehicle classification (car vs truck vs 18-wheeler)
- [ ] Weight class estimation
- [ ] Historical trend dashboards
- [ ] Alerting (congestion notifications)
- [ ] CI/CD pipeline

## Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

## License

[MIT](LICENSE)