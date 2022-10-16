from uuid import uuid4

from bot_battle_sdk.players import make_code
from bot_battle_sdk.protocol import RunGameTask

from ..dispatcher.runner import get_game_results
from ..sample_bots.random_player import RandomPlayer


def test_runner():
    code = make_code(RandomPlayer)

    task = RunGameTask(
        game_id=uuid4(), callback="https://test.com/", blue_code=code, red_code=code
    )

    results = get_game_results(task)
