import os
import random
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


MINIMUM_GAMES_PER_VERSION = 10
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


@ensure(
    lambda result: all(blue.id != red.id for blue, red in result),
    "Should not match a bot with itself",
)
def schedule_games():
    # choose bots with least number of games during the last 7 days
    bots_to_run = bots_with_not_enough_games().all()

    info(f"Found {len(bots_to_run)} bot(s) to schedule")

    bots_to_match = bots_to_run.copy()

    if (
        len(bots_to_match) < MINIMUM_GAMES_PER_VERSION
    ):  # first try to match new bots among themselves
        # choose opponents for them among all others
        bwneg = bots_with_not_enough_games().subquery()

        bots_to_match.extend(
            bots_with_code()
            .join(Participant, Participant.bot_id == Bot.id)
            .join(bwneg, Bot.id != bwneg.c.id)
            .group_by(Bot.id)
            .order_by(func.count(Participant.id).desc())
            .limit(MINIMUM_GAMES_PER_VERSION - len(bots_to_match))
            .all()
        )

    info(f"Found {len(bots_to_match)} bot(s) to match")

    random.shuffle(bots_to_run)
    random.shuffle(bots_to_match)

    combinations = []
    for bot in bots_to_run:
        self_excluded = list(set(bots_to_match) - {bot})
        matches = random.choices(self_excluded, k=MINIMUM_GAMES_PER_VERSION)
        combinations.extend([[bot, match] for match in matches])

    return combinations


def bots_with_not_enough_games() -> Query:
    subq = bots_with_games_for_last_version().subquery("gflv")

    return (
        db()
        .query(Bot)
        .join(subq, Bot.id == subq.c.gflv_bot_id, isouter=True)
        .filter(or_(subq.c.gflv_games_count == None, subq.c.gflv_games_count < 10))
        .limit(MAX_BOTS_TO_SCHEDULE)
    )


def bots_with_games_for_last_version() -> Query:
    latest_versions = bots_latest_version_datetime().subquery("latest_versions")

    return (
        db()
        .query(
            Bot.id.label("gflv_bot_id"), func.count(Game.id).label("gflv_games_count")
        )
        .join(latest_versions, Bot.id == latest_versions.c.bot_id, isouter=True)
        .join(
            Participant,
            Bot.id == Participant.bot_id,
            isouter=True,
        )
        .join(Game, Game.id == Participant.game_id, isouter=True)
        .filter(
            Game.created_at
            > latest_versions.c.latest_version_datetime,  # only games for the last version
        )
        .group_by(Bot.id)
    )


def bots_latest_version_datetime() -> Query:
    return (
        db()
        .query(
            Bot.id.label("bot_id"),
            func.max(CodeVersion.created_at).label("latest_version_datetime"),
        )
        .join(CodeVersion, Bot.id == CodeVersion.bot_id)
        .group_by(Bot.id)
        .having(func.max(CodeVersion.created_at) != None)
    )


def bots_with_code() -> Query:
    return (
        db()
        .query(Bot)
        .join(CodeVersion, Bot.id == CodeVersion.bot_id)
        .filter(CodeVersion.id != None)
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


def prep_run_game_task(blue: Bot, red: Bot, game: Game) -> RunGameTask:
    return RunGameTask(
        blue_code=blue.load_latest_code(),
        red_code=red.load_latest_code(),
        game_id=game.id,
        callback=CALLBACK,
    )
