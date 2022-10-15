from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, JSON, DateTime, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID

from .database import Base

from bot_battle_sdk.sides import Side
from bot_battle_sdk.state import State

import json


class JSONState(TypeDecorator):
    impl = JSON

    @staticmethod
    def process_bind_param(value: State, dialect):
        processed = {
            "board": deep_process_list(value.board, Side, lambda x: x.value),
            "next_side": value.next_side.value,
        }
        return json.dumps(processed)

    @staticmethod
    def process_result_value(value, dialect):
        dictified = json.loads(value)
        return State(
            board=deep_process_list(dictified["board"], int, lambda x: Side(x)),
            next_side=Side(dictified["next_side"]),
        )


def deep_process_list(what, cls, func):
    return [
        deep_process_list(el, cls, func)
        if isinstance(el, list)
        else func(el)
        if isinstance(el, cls)
        else el
        for el in what
    ]


class BotModel(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String)
    requesting_games = Column(Boolean)

    def __repr__(self):
        return f"<BotModel(id={self.id})>"


class GameModel(Base):
    __tablename__ = "games"

    id = Column(UUID(as_uuid=True), primary_key=True)
    result = Column(JSON)
    winner_id = Column(Integer)

    def __repr__(self):
        return f"<GameModel(result={self.result})>"


class StateModel(Base):
    __tablename__ = "states"

    id = Column(UUID(as_uuid=True), primary_key=True)
    game_id = Column(UUID(as_uuid=True))
    state = Column(JSONState)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class ParticipantModel(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(UUID(as_uuid=True))
    bot_id = Column(Integer)
    side = Column(Integer)
    acknowledged = Column(Boolean)
