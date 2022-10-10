import pytest
from fastapi.testclient import TestClient
from ..dispatcher.webserver import app
from bot_battle_sdk.protocol import ClientData


@pytest.fixture
def client():
    yield TestClient(app)


def test_properties(client):
    body = ClientData(token="", starting_port=0, max_sockets=0).json()
    # body = {"client_data": ClientData(token="", starting_port=0, max_sockets=0).json()}
    print(body)
    result = client.post("/", data=body)
    print(result.text)
    result.raise_for_status()
