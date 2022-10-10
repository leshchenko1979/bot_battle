from pydantic import BaseModel, UUID4

from .sides import Side
from .state import State

from enum import Enum


class GameResultType(Enum):
    ABORTED = 0
    VICTORY = 1
    TIE = 2


class GameResult(BaseModel):
    result_type: GameResultType
    winner: Side | None


class GameStateResponse(BaseModel):
    state: State
    result: GameResult = None


class WaitResponse(BaseModel):
    seconds: int


class GameListResponse(BaseModel):
    game_ids: list[UUID4]
