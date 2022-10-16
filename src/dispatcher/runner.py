from logging import info

import httpx
from bot_battle_sdk.players import PlayerAbstract
from bot_battle_sdk.sides import Side
from bot_battle_sdk.state import State
from fastapi import BackgroundTasks, FastAPI

from bot_battle_sdk.protocol import Code, GameLog, RunGameTask

app = FastAPI()


@app.post("/")
async def accept_task(self, task: RunGameTask, background: BackgroundTasks):
    info("Starting game")
    background.add_task(run_game, task)


async def run_game(task: RunGameTask):
    info(
        f"Starting a game between {task.blue_code.cls_name} and {task.red_code.cls_name}"
    )

    states, winners = get_game_results(task)

    # post results
    httpx.post(
        task.callback,
        json=GameLog(
            game_id=task.game_id,
            states=states,
            winner=winners[0] if len(winners) == 1 else None,
        ),
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


def init_bot(code: Code, side: Side) -> PlayerAbstract:
    exec(code.source, globals())
    return globals()[code.cls_name](side)
