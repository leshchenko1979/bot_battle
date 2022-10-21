import threading
from asyncio import Queue
from logging import basicConfig, getLogger
from threading import Thread
from traceback import format_exc

import httpx
import reretry
from botbattle import (
    Code,
    ExceptionInfo,
    GameLog,
    PlayerAbstract,
    RunGameTask,
    Side,
    State,
    StateException,
    init_bot,
)
from common.utils import run_once
from fastapi import BackgroundTasks, FastAPI
from icontract import ViolationError


class RunnerException(Exception):
    ...


class HangsException(RunnerException):
    ...


class InvalidMoveException(RunnerException):
    ...


class RaisesException(RunnerException):
    ...


class MoveBrakesRulesException(RunnerException):
    ...


MOVE_TIMEOUT = 0.1

ERROR_MESSAGES = {
    HangsException: f"Didn't receive a move in alloted time ({int(MOVE_TIMEOUT * 1000)}ms)",
    InvalidMoveException: "make_move() returned an invalid move",
    RaisesException: "make_move() raised an exception",
    MoveBrakesRulesException: "Made a move that breaks the rules",
}


app = FastAPI()

basicConfig(level="DEBUG")

logger = getLogger(__name__)
info = logger.info
debug = logger.debug

result_queue = Queue()


@app.post("/")
async def accept_task(task: RunGameTask, background: BackgroundTasks):
    info("Starting game")
    background.add_task(run_game, task)
    background.add_task(run_once, process_result_queue)


async def run_game(task: RunGameTask):
    info(
        f"Starting a game between {task.blue_code.cls_name} and {task.red_code.cls_name}"
    )

    log = GameLog(game_id=task.game_id, states=states)

    try:
        states, winners = await get_game_results(task.blue_code, task.red_code)
        log.winner = winners[0] if len(winners) == 1 else None

    except RunnerException as exc:
        msg = "\n".join([ERROR_MESSAGES[type(exc)], exc.args[1:]])
        log.exception = ExceptionInfo(msg=msg, caused_by_side=exc.args[0])

    await result_queue.put((task.callback, log))


async def get_game_results(blue_code: Code, red_code: Code):
    # load code
    blue, red = [
        init_bot(code, side)
        for code, side in ((blue_code, Side.BLUE), (red_code, Side.RED))
    ]

    # set initial state
    state = State(next_side=Side.BLUE)
    cur_bot: PlayerAbstract = blue
    states = []
    move = None

    def make_move():
        nonlocal move
        move = cur_bot.make_move(state)

    def handle_exception(*args):
        nonlocal make_move_exc
        make_move_exc = format_exc()

    # make moves
    while True:
        states.append(state.copy(deep=True))

        winners = state.winners()
        if winners:
            break

        make_move_exc = None
        threading.excepthook = handle_exception
        th = Thread(target=make_move)
        th.start()
        th.join(MOVE_TIMEOUT)

        if th.is_alive():
            raise HangsException(cur_bot.side)

        if make_move_exc:
            raise RaisesException(cur_bot.side, make_move_exc)

        try:
            state.drop_token(move)

        except ViolationError:
            raise InvalidMoveException(cur_bot.side, format_exc())

        except StateException:
            raise MoveBrakesRulesException(cur_bot.side, format_exc())

        # switch to next side
        cur_bot = blue if cur_bot == red else red

    return states, winners


async def process_result_queue():
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            callback, log = await result_queue.get()
            info(f"Posting result for game {log.game_id}")
            await try_post_results(client, callback, log)


@reretry.retry(ConnectionRefusedError, delay=3, jitter=1, backoff=1.5)
async def try_post_results(client: httpx.AsyncClient, callback: str, log: GameLog):
    await client.post(callback, content=log.json().encode("utf-8"))
