from sqlalchemy import ARRAY, Boolean, Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class BotModel(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(UUID)
    alive = Column(Boolean)

    host = Column(String)

    starting_port = Column(Integer)
    max_sockets = Column(Integer)

    def __repr__(self):
        return f"<BotModel(id={self.id}, alive={self.alive})>"


class GameModel(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    participants = Column(ARRAY(Integer))
    winner = Column(Integer)

    def __repr__(self):
        return f"<GameModel(participants={self.participants}, winner={self.winner})>"
