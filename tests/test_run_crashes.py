import time

import pytest
from botbattle import PlayerAbstract
from botbattle.players import make_code
from runner.runner import (
    ERROR_MESSAGES,
    HangsException,
    InvalidMoveException,
    MoveBrakesRulesException,
    RaisesException,
    get_game_results,
)


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


@pytest.mark.parametrize(
    "player, expected_exception, tb_info, move_info",
    [
        [Hangs, HangsException, False, False],
        [InvalidMove, InvalidMoveException, True, True],
        [Raises, RaisesException, True, False],
        [MoveBrakesRules, MoveBrakesRulesException, True, True],
    ],
)
async def test_run_crashes(player, expected_exception, tb_info, move_info):
    log_dict = await get_game_results(make_code(player), make_code(player))
    if "exception" not in log_dict:
        raise RuntimeError("Should have thrown an exception")

    exc = log_dict["exception"]

    assert ERROR_MESSAGES[expected_exception] in exc.msg

    if tb_info:
        assert "\nTraceback" in exc.msg

    if not move_info:
        assert exc.move is None
