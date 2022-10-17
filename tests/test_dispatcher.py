from uuid import uuid4

import pytest
from common.database import db
from common.models import Bot, Game
from dispatcher.dispatcher import app, prep_run_game_task, run_games, schedule_games
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    yield TestClient(app)


def test_schedule_games():
    schedule_games()


async def test_run_games():
    await run_games()


def test_prep_run_game_task():
    bot_1, bot2 = (db().query(Bot).filter(Bot.id == id).first() for id in (1, 2))
    game = Game()
    game.id = uuid4()
    task = prep_run_game_task(bot_1, bot2, game)
