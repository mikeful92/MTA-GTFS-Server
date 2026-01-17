import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_next_trains_endpoint(client):
    response = client.get('/next_trains')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, dict)
    assert "meta" in json_data
    assert "status" in json_data
    assert "Q_S" in json_data
    assert "Q_N" in json_data
    assert "6_S" in json_data
    assert "6_N" in json_data

def test_next_trains_format(client):
    response = client.get('/next_trains')
    assert response.status_code == 200
    json_data = response.get_json()

    for key in ("Q_S", "Q_N", "6_S", "6_N"):
        assert key in json_data
        trains = json_data[key]
        assert isinstance(trains, list)
        expected_direction = key.split("_")[1]

        last_minutes = -1
        for train in trains:
            assert isinstance(train, dict)
            assert "minutes_until" in train
            assert "destination" in train
            assert "direction" in train

            # ✅ NEW: check that time is non-negative and ascending
            minutes = train["minutes_until"]
            assert isinstance(minutes, int)
            assert minutes >= 0
            assert minutes >= last_minutes
            last_minutes = minutes

            assert isinstance(train["destination"], str)
            assert train["direction"] == expected_direction

    badges = {
        json_data["status"]["Q"]["badge"],
        json_data["status"]["6"]["badge"],
    }
    assert badges.issubset({"OT", "UNK"})

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert isinstance(json_data, dict)
    assert json_data.get("status") == "ok"
    assert "cache_age_seconds" in json_data
    assert "last_refresh" in json_data
