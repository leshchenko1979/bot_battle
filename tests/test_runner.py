from uuid import uuid4

from botbattle import make_code, RunGameTask

from runner.runner import get_game_results, accept_task
from sample_bots.random_player import RandomPlayer

from fastapi import BackgroundTasks


def test_get_game_results():
    code = make_code(RandomPlayer)

    task = RunGameTask(
        game_id=uuid4(), callback="https://test.com/", blue_code=code, red_code=code
    )

    results = get_game_results(task)

async def test_accept_task():
    code = make_code(RandomPlayer)

    task = RunGameTask(
        game_id=uuid4(), callback="https://test.com/", blue_code=code, red_code=code
    )

    await accept_task(task, BackgroundTasks())
