from bot_battle_sdk.protocol import (
    GameListResponse,
    GameResult,
    GameResultType,
    GameStateResponse,
    WaitResponse,
)
from fastapi import BackgroundTasks, FastAPI, Request
from pydantic import UUID4

from .database import db

app = FastAPI()

from logging import basicConfig, info

basicConfig(level="DEBUG")


@app.get("games/new/")
def new_game() -> GameStateResponse | WaitResponse:
    # check token
    # check if game limit exhausted
    # register new game request
    # find a match
    # create a game
    # return game_id
    ...


@app.get("games/{game_id}/state/last")
def state(game_id: UUID4) -> GameStateResponse:
    # check token
    # find the game
    # return game state
    ...


@app.post("games/{game_id}/move/?col={move}")
def move(game_id: UUID4, move: int) -> GameStateResponse:
    # check token
    # find the game
    # check game state
    # make move
    # wait for the opponent to make a move
    # return game state
    ...


@app.get("games/list/")
def games_list() -> GameListResponse:
    # check token
    # return game list
    ...
