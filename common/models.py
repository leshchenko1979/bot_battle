import json
from datetime import datetime, timezone

from botbattle import Code, Side, State
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID

from .database import Base, db


class JSONBoard(TypeDecorator):
    impl = JSON

    @staticmethod
    def process_bind_param(value: list[list[Side]], dialect):
        processed = deep_process_list(value, Side, lambda x: x.value)
        return json.dumps(processed)

    @staticmethod
    def process_result_value(value, dialect):
        dictified = json.loads(value)
        return deep_process_list(dictified["board"], int, lambda x: Side(x))


def deep_process_list(what, cls, func):
    return [
        deep_process_list(el, cls, func)
        if isinstance(el, list)
        else func(el)
        if isinstance(el, cls)
        else el
        for el in what
    ]


class CodeVersion(Base):
    __tablename__ = "code_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    bot_id = Column(Integer)
    source = Column(String)
    cls_name = Column(String)

    def __init__(self, bot_id, source, cls_name):
        self.bot_id = bot_id
        self.source = source
        self.cls_name = cls_name


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String)
    suspended = Column(Boolean)

    def __repr__(self):
        return f"<Bot(id={self.id})>"

    def load_latest_code(self) -> Code:
        latest_version: CodeVersion = (
            db()
            .query(CodeVersion)
            .filter_by(bot_id=self.id)
            .order_by(CodeVersion.created_at.desc())
            .first()
        )
        return Code(source=latest_version.source, cls_name=latest_version.cls_name)


class Game(Base):
    __tablename__ = "games"

    id = Column(UUID(as_uuid=True), primary_key=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    winner_id = Column(Integer)

    def __repr__(self):
        return f"<Game(winner={self.winner_id})>"


class StateModel(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True)
    game_id = Column(UUID(as_uuid=True))
    serial_no_within_game = Column(Integer)
    board = Column(JSONBoard)
    next_side = Column(Integer)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    def __init__(self, game_id, serial_no_within_game, board, next_side):
        self.game_id = game_id
        self.serial_no_within_game = serial_no_within_game
        self.board = board
        self.next_side = next_side


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    game_id = Column(UUID(as_uuid=True))
    bot_id = Column(Integer)
    side = Column(Integer)
    result = Column(String)
    exception = Column(String)
