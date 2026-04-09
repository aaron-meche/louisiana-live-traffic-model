from la_traffic.main import app


def test_app_title() -> None:
    assert app.title == "Louisiana Live Traffic Model API"
