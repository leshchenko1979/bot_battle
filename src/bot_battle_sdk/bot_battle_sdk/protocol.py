from pydantic import BaseModel, UUID4

from .sides import Side
from .state import State

from typing import Literal


GameResultType = Literal["running", "aborted", "victory", "tie"]

class GameStateResponse(BaseModel):
    state: State
    your_side: Side
    result: GameResultType

class GameStateResponseVictory(GameStateResponse):
    result: Literal["victory"]
    winner: Side

class NewGameResponseType(BaseModel):
    response_type: Literal["created", "wait"]

class NewGameResponseCreated(NewGameResponseType):
    response_type: Literal["created"]
    game_id: UUID4

class NewGameResponseWait(NewGameResponseType):
    response_type: Literal["wait"]
    wait_for: int

class NewGameResponse(BaseModel):
    response: NewGameResponseWait | NewGameResponseCreated

class GameListResponse(BaseModel):
    game_ids: list[UUID4]
