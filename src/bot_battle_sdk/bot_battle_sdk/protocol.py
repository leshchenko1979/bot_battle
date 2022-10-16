from pydantic import BaseModel, UUID4, HttpUrl

from .sides import Side
from .state import State


class Code(BaseModel):
    source: str
    cls_name: str


class RunGameTask(BaseModel):
    game_id: UUID4
    callback: HttpUrl
    blue_code: Code
    red_code: Code


class GameLog(BaseModel):
    game_id: UUID4
    states: list[State]
    winner: Side | None
