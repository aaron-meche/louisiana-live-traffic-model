from la_traffic.detection.tracker import count_vehicles


def test_count_vehicles_counts_input() -> None:
    assert count_vehicles([{"id": 1}, {"id": 2}]) == 2
