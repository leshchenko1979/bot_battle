import pytest
from dispatcher.dispatcher import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    yield TestClient(app)
