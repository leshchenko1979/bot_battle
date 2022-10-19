import itertools as it
import os
import random
from datetime import datetime, timedelta, timezone
from logging import basicConfig, getLogger
from uuid import uuid4

import httpx
from botbattle import RunGameTask, Side
from common.database import db
from common.models import Bot, CodeVersion, Game, Participant
from common.utils import LeakyBucket
from fastapi import FastAPI
from icontract import ensure
from sqlalchemy import or_
from sqlalchemy.orm import Query
from sqlalchemy.sql import func

app = FastAPI()

basicConfig(level="DEBUG")

logger = getLogger(__name__)
info = logger.info
debug = logger.debug
warning = logger.warning


GAMES_IN_A_DAY = 10
MAX_BOTS_TO_SCHEDULE = 100
MAX_GAMES_TO_SCHEDULE = 100
RUNNER_URL = os.environ["RUNNER_URL"]
CALLBACK = os.environ["DISPATCHER_URL"] + "/game_result"
BUCKET_SIZE = 10
REQUESTS_PER_MINUTE = 60


@app.on_event("startup")
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
            try:
                httpx.post(RUNNER_URL, content=task.json().encode("utf-8"))
            except httpx.ConnectError:
                warning("Failed to submit to runner at {0}".format(RUNNER_URL))


def bots_with_code():
    return (
        db()
        .query(Bot)
        .join(CodeVersion, Bot.id == CodeVersion.bot_id)
        .filter(CodeVersion.id != None)
    )


def prep_run_game_task(blue: Bot, red: Bot, game: Game) -> RunGameTask:
    # load code
    blue_code, red_code = (bot.load_latest_code() for bot in (blue, red))

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
