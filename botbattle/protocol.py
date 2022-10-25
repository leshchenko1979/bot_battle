from datetime import datetime
from typing import Any
from pydantic import BaseModel, UUID4, AnyHttpUrl

from .side import Side
from .state import State


class Code(BaseModel):
    source: str
    cls_name: str


class RunGameTask(BaseModel):
    game_id: UUID4
    callback: AnyHttpUrl
    blue_code: Code
    red_code: Code


class ExceptionInfo(BaseModel):
    msg: str
    caused_by_side: Side
    move: Any


class GameLog(BaseModel):
    game_id: UUID4
    states: list[State]
    winner: Side | None
    exception: ExceptionInfo | None


class ParticipantInfo(BaseModel):
    created_at: datetime
    result: str
    exception: ExceptionInfo | None


class VersionStats(BaseModel):
    victories: int
    losses: int
    ties: int


class VersionInfo(BaseModel):
    created_at: datetime
    loc: int
    exception: ExceptionInfo | None
    stats: VersionStats | None
