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
    assert 'N' in json_data or 'S' in json_data or 'error' in json_data

def test_next_trains_format(client):
    response = client.get('/next_trains')
    assert response.status_code == 200

    json_data = response.get_json()
    assert isinstance(json_data, dict)

    # Check that the response contains 'N' and/or 'S'
    assert any(key in json_data for key in ('N', 'S'))

    for direction, trains in json_data.items():
        assert direction in ('N', 'S')
        assert isinstance(trains, list)

        for train in trains:
            assert isinstance(train, dict)
            assert 'arrival_time' in train
            assert 'destination' in train
            assert 'direction' in train

            # Validate format of arrival_time
            from datetime import datetime
            arrival_time = train['arrival_time']
            try:
                datetime.fromisoformat(arrival_time)
            except ValueError:
                pytest.fail(f"Invalid ISO 8601 format: {arrival_time}")

            assert train['direction'] in ('N', 'S')
            assert isinstance(train['destination'], str)
