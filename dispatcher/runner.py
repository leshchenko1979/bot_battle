from logging import getLogger

import httpx
from botbattle import GameLog, PlayerAbstract, RunGameTask, Side, State, init_bot
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

logger = getLogger(__name__)
info = logger.info
debug = logger.debug


@app.post("/")
async def accept_task(task: RunGameTask, background: BackgroundTasks):
    info("Starting game")
    background.add_task(run_game, task)


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
    # post results
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            task.callback,
            content=log.json().encode("utf-8"),
        )


def get_game_results(task):
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
