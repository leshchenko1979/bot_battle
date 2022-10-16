import asyncio
from datetime import datetime, timedelta, timezone
from logging import debug, info
from uuid import uuid4

import httpx
from bot_battle_sdk.protocol import Code, GameLog, RunGameTask
from bot_battle_sdk.sides import Side
from bot_battle_sdk.state import State
from fastapi import FastAPI, Request, BackgroundTasks
from sqlalchemy.sql import func
from sqlalchemy.orm import Query

from .database import db
from .models import Bot, CodeVersion, Game, Participant, StateModel
from .utils import LeakyBucket

app = FastAPI()

GAMES_IN_A_DAY = 10
MAX_BOTS_TO_SCHEDULE = 100
RUNNER_URL = "http://localhost:8201"
CALLBACK = "http://localhost:8200/game_result"
BUCKET_SIZE = 10
REQUESTS_PER_MINUTE = 60


@app.post("/update_code")
async def update_code(code: Code, request: Request, background: BackgroundTasks):
    background.add_task(run_once, schedule_games)

    bot = extract_bot(request)

    last_version: CodeVersion = (
        db()
        .query(CodeVersion)
        .filter_by(bot_id=bot.id)
        .order_by(CodeVersion.created_at.desc())
        .first()
    )

    if (
        last_version
        and last_version.source == code.source
        and last_version.cls_name == code.cls_name
    ):
        return

    new_version = CodeVersion()
    new_version.bot_id = bot.id
    new_version.source = code.source
    new_version.cls_name = code.cls_name
    db().add(new_version)
    db().commit()


@app.post("/game_result")
async def game_result(result: GameLog):
    participants: list[Participant] = (
        db().query(Participant).filter(Participant.game_id == result.game_id).all()
    )

    assert len(participants) == 2

    # save results for participants
    if result.winner:
        game: Game = db().query(Game).filter(Game.id == result.game_id).one()

        if Side(participants[0].side) == result.winner:
            part_results = ("victory", "loss")
            game.winner_id = participants[0].id
        else:
            part_results = ("loss", "victory")
            game.winner_id = participants[1].id

    else:
        part_results = ("tie", "tie")

    for participant, part_result in zip(participants, part_results):
        participant.result = part_result

    # save states
    for i, state in enumerate(result.states):
        state_model = StateModel()
        state_model.game_id = result.game_id
        state_model.serial_no_within_game = i
        state_model.board = state.board
        state_model.next_side = state.next_side
        db().add(state_model)

    db().commit()


def extract_bot(request: Request) -> Bot:
    token = request.headers["Authorization"].split()[-1]
    bot: Bot = db().query(Bot).filter_by(token=token).one()
    debug(f"Processing request from bot {bot.id}")
    return bot


def bots_with_code():
    return (
        db()
        .query(Bot)
        .join(CodeVersion, Bot.id == CodeVersion.bot_id)
        .filter(CodeVersion.id is not None)
    )


async def schedule_games():
    info("Starting schedule")

    # choose bots with least number of games during the last 7 days
    bots_to_run = bots_with_not_enough_games.all()

    info(f"Found {len(bots_to_run)} bot(s) to schedule")

    # choose opponents for them among all others
    bots_to_match = (
        bots_with_code().filter(Bot not in bots_to_run).limit(len(bots_to_run)).all()
    )

    info(f"Found {len(bots_to_match)} bot(s) to match")

    # start games
    leaky_bucket = LeakyBucket(
        bucket_size=BUCKET_SIZE, requests_per_minute=REQUESTS_PER_MINUTE
    )

    for blue, red in zip(bots_to_run, bots_to_match):
        async with leaky_bucket.throttle():
            # record the game is running
            game = Game()
            game.id = uuid4()
            db().add(game)

            for bot, side in [[blue, Side.BLUE], [red, Side.RED]]:
                participant = Participant()
                participant.game_id = game.id
                participant.bot_id = bot.id
                participant.side = side.value
                db().add(participant)

            db().commit()

            # load code
            blue_code, red_code = (load_latest_code(bot) for bot in (blue, red))

            # compose payload
            task = RunGameTask(
                blue_code=blue_code,
                red_code=red_code,
                game_id=game.id,
                callback=CALLBACK,
            )

            # submit to a runner
            httpx.post(RUNNER_URL, json=task.dict())


def bots_with_not_enough_games() -> Query:
    return (
        bots_with_code()
        .join(Participant, Bot.id == Participant.bot_id)
        .join(
            Game,
            Game.id == Participant.game_id,
        )
        .filter(Game.created_at > datetime.now(timezone.utc) - timedelta(days=1))
        .group_by(Bot.id)
        .having(func.count(Game.id) < GAMES_IN_A_DAY)
        .limit(MAX_BOTS_TO_SCHEDULE)
    )


def load_latest_code(bot: Bot) -> Code:
    latest_version: CodeVersion = (
        db()
        .query(CodeVersion)
        .filter_by(bot_id=bot.id)
        .order_by(CodeVersion.created_at.desc())
        .first()
    )
    return Code(source=latest_version.source, cls_name=latest_version.cls_name)


_already_run = set()


async def run_once(func, *args, **kwargs):
    global _already_run
    if func in _already_run:
        return
    _already_run.add(func)
    return await func(*args, **kwargs)
