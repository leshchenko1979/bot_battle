import asyncio
import random
from datetime import datetime, timedelta, timezone
from logging import getLogger
from uuid import uuid4

import httpx
from botbattle import Code, GameLog, RunGameTask, Side, State
from fastapi import BackgroundTasks, FastAPI, Request
from icontract import ensure
from sqlalchemy import or_
from sqlalchemy.orm import Query
from sqlalchemy.sql import func
import itertools as it

from .database import db
from .models import Bot, CodeVersion, Game, Participant, StateModel
from .utils import LeakyBucket, run_once

app = FastAPI()

logger = getLogger(__name__)
info = logger.info
debug = logger.debug
warning = logger.warning


GAMES_IN_A_DAY = 10
MAX_BOTS_TO_SCHEDULE = 100
MAX_GAMES_TO_SCHEDULE = 100
RUNNER_URL = "http://localhost:8201/"
CALLBACK = "http://localhost:8200/game_result"
BUCKET_SIZE = 10
REQUESTS_PER_MINUTE = 60


@app.post("/update_code")
async def update_code(code: Code, request: Request, background: BackgroundTasks):
    # start running games
    background.add_task(run_once, run_games)

    # find the bot
    bot = extract_bot(request)

    # load last code version
    last_version = load_latest_code(bot)

    # if nothing changed then quit
    if last_version and last_version == code:
        return

    # else save new code version
    new_version = CodeVersion()
    new_version.bot_id = bot.id
    new_version.source = code.source
    new_version.cls_name = code.cls_name
    db().add(new_version)
    db().commit()


@app.post("/game_result")
async def game_result(result: GameLog, background: BackgroundTasks):
    background.add_task(save_game_result, result)


async def save_game_result(result: GameLog):
    participants: list[Participant] = (
        db().query(Participant).filter(Participant.game_id == result.game_id).all()
    )

    assert len(participants) == 2

    # save results for participants
    if result.winner:
        game: Game = db().query(Game).filter(Game.id == result.game_id).one()

        if Side(participants[0].side) == result.winner:
            part_results = ("victory", "loss")
            game.winner_id = participants[0].bot_id
        else:
            part_results = ("loss", "victory")
            game.winner_id = participants[1].bot_id

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
        state_model.next_side = state.next_side.value
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
        .filter(CodeVersion.id != None)
    )


async def run_games():
    info("Starting schedule")

    # start games
    leaky_bucket = LeakyBucket(
        bucket_size=BUCKET_SIZE, requests_per_minute=REQUESTS_PER_MINUTE
    )

    for blue, red in schedule_games():
        # don't match a bot with itself
        if blue.id == red.id:
            continue

        async with leaky_bucket.throttle():
            warning("Starting a game")
            game = save_new_game(blue, red)
            task = prep_run_game_task(blue, red, game)

            # submit to a runner
            httpx.post(RUNNER_URL, content=task.json().encode("utf-8"))


def prep_run_game_task(blue: Bot, red: Bot, game: Game) -> RunGameTask:
    # load code
    blue_code, red_code = (load_latest_code(bot) for bot in (blue, red))

    return RunGameTask(
        blue_code=blue_code,
        red_code=red_code,
        game_id=game.id,
        callback=CALLBACK,
    )


def save_new_game(blue: Bot, red: Bot) -> Game:
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

    return game


@ensure(
    lambda result: all(blue.id != red.id for blue, red in result),
    "Should not match a bot with itself",
)
def schedule_games():
    # choose bots with least number of games during the last 7 days
    bots_to_run = bots_with_not_enough_games().all()

    info(f"Found {len(bots_to_run)} bot(s) to schedule")

    # choose opponents for them among all others
    bots_to_match = (
        bots_with_code()
        .filter(Bot.id not in [bot.id for bot in bots_to_run])
        .limit(len(bots_to_run))
        .all()
    )

    info(f"Found {len(bots_to_match)} bot(s) to match")

    if len(bots_to_run) > len(bots_to_match):
        bots_to_match.extend(
            random.sample(bots_to_run, len(bots_to_run) - len(bots_to_match))
        )

    random.shuffle(bots_to_run)
    random.shuffle(bots_to_match)

    correct_combinations = filter(
        lambda x: x[0].id != x[1].id, it.product(bots_to_run, bots_to_match)
    )

    return list(it.islice(it.cycle(correct_combinations), MAX_GAMES_TO_SCHEDULE))


def bots_with_not_enough_games() -> Query:
    return (
        bots_with_code()
        .join(Participant, Bot.id == Participant.bot_id, isouter=True)
        .join(Game, Game.id == Participant.game_id, isouter=True)
        .filter(
            or_(
                Game.id == None,
                Game.created_at > datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
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
