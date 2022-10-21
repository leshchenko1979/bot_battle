from uuid import uuid4

import pytest
from common.database import db
from common.models import Bot, Game
from dispatcher.dispatcher import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    yield TestClient(app)
