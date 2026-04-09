from la_traffic.ingestion.camera import discover_cameras


def test_discover_cameras_returns_list() -> None:
    assert isinstance(discover_cameras(), list)
