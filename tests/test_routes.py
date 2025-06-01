import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_next_trains(client):
    response = client.get('/next_trains')
    assert response.status_code == 200
    assert isinstance(response.json, dict)
