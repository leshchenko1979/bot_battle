import collections
import os
from datetime import datetime
from logging import basicConfig, getLogger

import httpx
from botbattle import (
    Code,
    ExceptionInfo,
    GameLog,
    ParticipantInfo,
    Side,
    VersionInfo,
    VersionStats,
)
from common.database import SessionLocal
from common.models import Bot, CodeVersion, Game, Participant, StateModel
from fastapi import BackgroundTasks, FastAPI, Request
from sqlalchemy.orm import Session

app = FastAPI()

basicConfig(level="DEBUG")

logger = getLogger(__name__)
info = logger.info
debug = logger.debug
warning = logger.warning


@app.post("/update_code")
async def update_code(code: Code, request: Request) -> dict:
    with SessionLocal.begin() as db:
        # find the bot
        bot = extract_bot(request, db)

        # load last code version
        last_version = bot.load_latest_code(db)

        # if nothing changed then quit
        if last_version and last_version == code:
            return {"updated": False}

        # else save new code version
        new_version = CodeVersion(bot.id, code.source, code.cls_name)
        bot.suspended = False

        db.add(new_version)

    httpx.post(os.environ["SCHEDULER_URL"])

    return {"updated": True}


@app.post("/game_result")
async def game_result(result: GameLog, background: BackgroundTasks):
    background.add_task(save_game_result, result)


async def save_game_result(result: GameLog):
    info(f"Saving game {result.game_id} result")

    with SessionLocal.begin() as db:
        participants: list[Participant] = (
            db.query(Participant).filter_by(game_id=result.game_id).all()
        )

        assert len(participants) == 2

        if result.exception:
            game: Game = db.get(Game, result.game_id)

            if result.exception.caused_by_side == Side(participants[0].side):
                part_results = ("crashed", "opponent_crashed")
                perpetrator_idx = 0

            else:
                part_results = ("opponent_crashed", "crashed")
                perpetrator_idx = 1

            participants[perpetrator_idx].exception = result.exception.json()

            # mark the bot that caused the crash as suspended
            bot: Bot = db.get(Bot, participants[perpetrator_idx].bot_id)
            bot.suspended = True

        elif result.winner:
            game: Game = db.get(Game, result.game_id)

            if Side(participants[0].side) == result.winner:
                part_results = ("victory", "loss")
                game.winner_id = participants[0].bot_id
            else:
                part_results = ("loss", "victory")
                game.winner_id = participants[1].bot_id

        else:
            part_results = ("tie", "tie")

        # save results for participants
        for participant, part_result in zip(participants, part_results):
            participant.result = part_result

        # save states
        for i, state in enumerate(result.states):
            state_model = StateModel(
                result.game_id, i, state.board, state.next_side.value
            )
            db.add(state_model)


@app.get("/get_part_info/")
async def get_part_info(
    after: datetime | None = None, request: Request = None
) -> list[ParticipantInfo]:
    with SessionLocal.begin() as db:
        bot = extract_bot(request, db)

        part_query = (
            db.query(Participant)
            .filter_by(bot_id=bot.id)
            .filter(Participant.result != None)
        )

        if after:
            part_query = part_query.filter(Participant.created_at > after)

        part_query = part_query.order_by(Participant.created_at.desc()).limit(20)

        participants: list[Participant] = part_query.all()

        return [
            ParticipantInfo(
                created_at=part.created_at,
                result=part.result,
                exception=ExceptionInfo.parse_raw(part.exception),
            )
            for part in reversed(participants)
        ]


@app.get("/latest_versions_info/")
async def get_part_info(request: Request = None) -> list[VersionInfo]:
    with SessionLocal.begin() as db:
        db: Session = db  # to allow IDE type hinting

        bot = extract_bot(request, db)

        # get the latest versions
        query = (
            db.query(CodeVersion)
            .filter_by(bot_id=bot.id)
            .order_by(CodeVersion.created_at.desc())  # recent first
            .limit(20)
        )

        versions: list[CodeVersion] = list(reversed(query.all()))  # recent last
        results: list[VersionInfo] = []

        # for each version
        for version, next_version in zip(versions, [*versions[1:], None]):
            entry = VersionInfo(
                created_at=version.created_at, loc=str(version.source).count("\n")
            )

            # find all games
            query = (
                db.query(Participant)
                .filter_by(bot_id=bot.id)
                .filter(version.created_at < Participant.created_at)
            )

            if next_version:
                query = query.filter(Participant.created_at < next_version.created_at)

            parts: list[ParticipantInfo] = query.all()

            # check if crashed
            exc = [part.exception for part in parts if part.exception]
            if exc:
                entry.exception = ExceptionInfo.parse_raw(exc[-1])

            # else calc stats
            else:
                counts = collections.Counter(
                    part.result for part in parts if part.result
                )
                entry.stats = VersionStats(
                    victories=counts.get("victory", 0),
                    losses=counts.get("loss", 0),
                    ties=counts.get("tie", 0),
                )

            results.append(entry)

    return results


def extract_bot(request: Request, db: Session) -> Bot:
    token = request.headers["Authorization"].split()[-1]
    bot: Bot = db.query(Bot).filter_by(token=token).one()
    debug(f"Processing request from bot {bot.id}")
    return bot
