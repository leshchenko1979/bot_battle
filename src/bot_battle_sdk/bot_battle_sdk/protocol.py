from pydantic import BaseModel, UUID4

from .sides import Side
from .state import State


class ClientData(BaseModel):
    token: str
    starting_port: int
    max_sockets: int


class StartingMessage(BaseModel):
    game_id: UUID4
    side: Side


class StateMessage(BaseModel):
    state: State


class MoveMessage(BaseModel):
    move: int


class ResultMessage(BaseModel):
    winner: Side
