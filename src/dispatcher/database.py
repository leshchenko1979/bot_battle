import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

database_uri = os.environ["DATABASE_URI"]

@lru_cache
def db():
    engine = create_engine(database_uri)
    return Session(engine)
