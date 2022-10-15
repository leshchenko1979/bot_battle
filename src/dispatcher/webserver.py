import asyncio
import logging
from logging import info, debug
from uuid import uuid4

from bot_battle_sdk.protocol import (
    GameResultType,
    GameStateResponse,
    NewGameResponseWait,
    NewGameResponseCreated,
    NewGameResponse,
)
from bot_battle_sdk.sides import Side
from bot_battle_sdk.state import State
from fastapi import FastAPI, Request, Response
from pydantic import UUID4
from starlette.background import BackgroundTask
from starlette.types import Message

from .database import db
from .models import BotModel, GameModel, ParticipantModel, StateModel

app = FastAPI()

ACTIVE_GAMES_WITH_BOT_LIMIT = 10
ACTIVE_GAMES_WITH_BOT_LIMIT_TIMEOUT = 10
OPPONENT_WAIT_CYCLE = 2
OPPONENT_WAIT_TIMEOUT = 10

WAIT_RESPONSE = NewGameResponse(
    response=NewGameResponseWait(
        response_type="wait", wait_for=ACTIVE_GAMES_WITH_BOT_LIMIT_TIMEOUT
    )
)


class GameEndedException(Exception):
    ...


def log_req_resp(request_body, response_body):
    logging.info(request_body.decode())
    logging.info(response_body.decode())


async def set_body(request: Request, body: bytes):
    async def receive() -> Message:
        return {"type": "http.request", "body": body}

    request._receive = receive


@app.middleware("http")
async def some_middleware(request: Request, call_next):
    request_body = await request.body()
    await set_body(request, request_body)
    response = await call_next(request)

    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    task = BackgroundTask(log_req_resp, request_body, response_body)
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
        background=task,
    )


@app.get("/games/new/")
async def new_game(request: Request) -> NewGameResponse:
    # check token
    bot = extract_bot(request)

    # check if game limit exhausted
    if active_games_with_bot(bot) >= ACTIVE_GAMES_WITH_BOT_LIMIT:
        return WAIT_RESPONSE

    # register new game request
    bot.requesting_games = True
    db().commit()

    # find a match
    game = await find_match(bot)

    return (
        NewGameResponse(
            response=NewGameResponseCreated(response_type="created", game_id=game.id)
        )
        if game
        else WAIT_RESPONSE
    )


@app.get("/games/{game_id}/wait_turn")
async def wait_my_turn(game_id: UUID4, request: Request) -> GameStateResponse:
    # check token
    bot = extract_bot(request)

    # find the game
    game = db().query(GameModel).filter_by(id=game_id).one()

    # find bot side
    side = get_bot_side(bot, game)

    game, state = await wait_side(game, side)

    # return game state
    return GameStateResponse(
        state=state,
        your_side=side,
        result=game.result,
        winner=game.winner,
    )


async def wait_side(game: GameModel, side: Side) -> tuple[GameModel, State]:
    if game.result != "running":
        raise GameEndedException

    # wait for the opponent to make a move
    while True:
        state = get_last_state(game)

        if state.next_side == side:
            # refresh game data
            game = db().query(GameModel).filter_by(id=game.id).one()
            return game, state

        await asyncio.sleep(OPPONENT_WAIT_CYCLE)


@app.post("/games/{game_id}/move/?col={col}")
async def move(game_id: UUID4, col: int, request: Request) -> GameStateResponse:
    # check token
    bot = extract_bot(request)

    # find the game
    game = db().query(GameModel).filter_by(id=game_id).one()

    # get_last_state
    state = get_last_state(game)

    # get bot side
    side = get_bot_side(bot, game)

    # check game state
    if state.next_side != side:
        raise RuntimeError("It's not your turn to move")

    # make move
    state.drop_token(col, side)
    state.next_side = side.next_side()

    state_model = StateModel()
    state_model.id = uuid4()
    state_model.game_id = game.id
    state_model.state = state.json()
    db().add(state_model)

    # calculate game result
    winners = state.winners()

    if len(winners) == 2:
        game.result = GameResultType.TIE.value
        db().commit()

    elif len(winners) == 1:
        game.result = GameResultType.VICTORY.value
        game.winner_id = bot.id if winners[0] == side else side.next_side()
        db().commit()

    else:
        db().commit()
        # wait for the opponent to move
        game, state = await wait_side(game, side)

    # return game state
    return GameStateResponse(
        state=state,
        your_side=side,
        result=game.result,
        winner=(winners[0] if len(winners) == 1 else None),
    )


def extract_bot(request: Request) -> BotModel:
    token = request.headers["Authorization"].split()[-1]
    bot: BotModel = db().query(BotModel).filter_by(token=token).one()
    debug(f"Processing request from bot {bot.id}")
    return bot


async def find_match(bot: BotModel):
    # look for scheduled but unacknowledged games
    part: ParticipantModel = (
        db()
        .query(ParticipantModel)
        .filter_by(bot_id=bot.id, acknowledged=False)
        .first()
    )

    if part:
        part.acknowledged = True
        return db().query(GameModel).filter_by(id=part.game_id).one()

    # look for other bots looking for games
    match: BotModel = (
        db()
        .query(BotModel)
        .filter(BotModel.id != bot.id, BotModel.requesting_games == True)
        .first()
    )

    # if not found
    if not match:
        # register self as looking for games
        bot.requesting_games = True
        return

    # if found
    match.requesting_games = False

    # create a game
    game = GameModel()
    game.id = uuid4()
    game.result = "running"
    db().add(game)

    # add participants
    for part_bot, side in ([bot, Side.BLUE], [match, Side.RED]):
        part = ParticipantModel()
        part.bot_id = part_bot.id
        part.game_id = game.id
        part.side = side.value
        part.acknowledged = part_bot == bot
        db().add(part)

    # add initial state
    state = StateModel()
    state.id = uuid4()
    state.game_id = game.id
    state.state = State(next_side=Side.BLUE)
    db().add(state)

    # save to database
    db().commit()

    return game


def active_games_with_bot(bot: BotModel) -> int:
    return (
        db()
        .query(GameModel)
        .join(ParticipantModel, GameModel.id == ParticipantModel.game_id)
        .filter(GameModel.result == "running")
        .filter(ParticipantModel.bot_id == bot.id)
        .count()
    )


def get_last_state(game: GameModel) -> State:
    return State(
        db()
        .query(StateModel)
        .filter_by(id=game.id)
        .order_by(StateModel.created_at.desc())
        .first()
        .state
    )


def get_bot_side(bot: BotModel, game: GameModel) -> Side:
    return Side(
        db().query(ParticipantModel).filter_by(id=bot.id, game_id=game.id).first().side
    )
