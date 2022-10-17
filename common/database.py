import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

database_uri = os.environ["DATABASE_URI"]


from sqlalchemy.log import InstanceLogger
import logging


def pretty_log(self, level, msg, *args, **kwargs):
    if self.logger.manager.disable >= level:
        return

    selected_level = self._echo_map[self.echo]
    if selected_level == logging.NOTSET:
        selected_level = self.logger.getEffectiveLevel()

    if level >= selected_level:

        import sqlparse

        msg = sqlparse.format(msg, reindent=True, keyword_case="upper")

        self.logger._log(level, "\n" + msg, args, **kwargs)


InstanceLogger.log = pretty_log


@lru_cache
def db():
    engine = create_engine(database_uri)
    engine.echo = False
    Session = sessionmaker(bind=engine)
    return Session()
