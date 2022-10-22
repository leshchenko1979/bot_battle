import threading
from asyncio import Queue
from logging import basicConfig, getLogger
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

    log_dict = await get_game_results(task.blue_code, task.red_code)

    log = GameLog(game_id=task.game_id, states=log_dict["states"])
    if "exception" in log_dict:
        log.exception = log_dict["exception"]
    else:
        log.winner = log_dict["winners"][0] if len(log_dict["winners"]) == 1 else None

    await result_queue.put((task.callback, log))


async def get_game_results(blue_code: Code, red_code: Code) -> dict:
    # load code
    blue, red = [
        init_bot(code, side)
        for code, side in ((blue_code, Side.BLUE), (red_code, Side.RED))
    ]

    # set initial state
    state = State(next_side=Side.BLUE)
    cur_bot: PlayerAbstract = blue
    states = []

    def make_move():
        nonlocal move
        move = cur_bot.make_move(state)

    def handle_exception(*args):
        nonlocal make_move_exc
        make_move_exc = format_exc()

    threading.excepthook = handle_exception

    # make moves
    while True:
        states.append(state.copy(deep=True))

        winners = state.winners()
        if winners:
            break

        move = None
        exc_msg = None
        make_move_exc = None

        th = threading.Thread(target=make_move)
        th.start()
        th.join(MOVE_TIMEOUT)

        if th.is_alive():
            exc_msg = ERROR_MESSAGES[HangsException]
            break

        if make_move_exc:
            exc_msg = ERROR_MESSAGES[RaisesException] + "\n" + make_move_exc
            break

        try:
            state.drop_token(move)

        except ViolationError:
            exc_msg = ERROR_MESSAGES[InvalidMoveException] + "\n" + format_exc()
            break

        except StateException:
            exc_msg = ERROR_MESSAGES[MoveBrakesRulesException] + "\n" + format_exc()
            break

        # switch to next side
        cur_bot = blue if cur_bot == red else red

    log = {"states": states}

    if exc_msg:
        log["exception"] = ExceptionInfo(
            msg=exc_msg, caused_by_side=cur_bot.side, move=move
        )

    if winners:
        log["winners"] = winners

    return log


async def process_result_queue():
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            callback, log = await result_queue.get()
            info(f"Posting result for game {log.game_id}")
            await try_post_results(client, callback, log)


@reretry.retry(ConnectionRefusedError, delay=3, jitter=1, backoff=1.5)
async def try_post_results(client: httpx.AsyncClient, callback: str, log: GameLog):
    await client.post(callback, content=log.json().encode("utf-8"))
