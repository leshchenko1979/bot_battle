from asyncio import Queue
from logging import basicConfig, getLogger

import httpx
import reretry
from botbattle import GameLog, PlayerAbstract, RunGameTask, Side, State, init_bot
from common.utils import run_once
from fastapi import BackgroundTasks, FastAPI

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

    states, winners = get_game_results(task)

    log = GameLog(
        game_id=task.game_id,
        states=states,
        winner=winners[0] if len(winners) == 1 else None,
    )

    await result_queue.put((task.callback, log))


def get_game_results(task: RunGameTask):
    # load code
    blue, red = [
        init_bot(code, side)
        for code, side in ((task.blue_code, Side.BLUE), (task.red_code, Side.RED))
    ]

    # set initial state
    state = State(next_side=Side.BLUE)
    cur_bot: PlayerAbstract = blue
    states = []

    # make moves
    while True:
        states.append(state.copy(deep=True))

        winners = state.winners()
        if winners:
            break

        move = cur_bot.make_move(state)
        state.drop_token(move)

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
