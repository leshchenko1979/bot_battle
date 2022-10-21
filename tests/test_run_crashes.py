import pytest
from botbattle import PlayerAbstract
import time
from runner.runner import get_game_results, RunnerException, RunnerErrorMessage
from sample_bots.random_player import RandomPlayer
from botbattle.players import make_code


class Hangs(PlayerAbstract):
    def make_move(self, board):
        for _ in range(10):
            time.sleep(0.1)

class InvalidMove(PlayerAbstract):
    def make_move(self, board):
        return "oops"

class Raises(PlayerAbstract):
    def make_move(self, board):
        raise RuntimeError

class MoveBrakesRules(PlayerAbstract):
    def make_move(self, board):
        return 0

@pytest.mark.parametrize("player, expected_result", [
    [Hangs, RunnerErrorMessage.HANGS],
    [InvalidMove, RunnerErrorMessage.INVALID_MOVE],
    [Raises, RunnerErrorMessage.RAISES],
    [MoveBrakesRules, RunnerErrorMessage.MOVE_BREAKS_RULES]
])
async def test_run_crashes(player, expected_result):
    try:
        await get_game_results(make_code(player), make_code(player))
        raise RuntimeError("Should have thrown an exception")

    except RunnerException as exc:
        assert expected_result.value == exc.args[0]
