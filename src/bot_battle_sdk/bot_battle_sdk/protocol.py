from pydantic import BaseModel, UUID4

from .sides import Side
from .state import State

from enum import Enum


class GameResultType(Enum):
    ABORTED = "aborted"
    VICTORY = "victory"
    TIE = "tie"


class GameResult(BaseModel):
    result_type: GameResultType
    winner: Side | None


class GameStateResponse(BaseModel):
    state: State
    your_side: Side = None
    result: GameResult = None


class NewGameResponseType(Enum):
    NEW_GAME_CREATED = "new_game_created"
    WAIT = "wait"


class NewGameResponse(BaseModel):
    response_type: NewGameResponseType
    game_id: UUID4 = None
    wait_for: int = None


class GameListResponse(BaseModel):
    game_ids: list[UUID4]
