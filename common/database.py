import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.log import InstanceLogger
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

database_uri = os.environ["DATABASE_URI"]


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


engine = create_engine(database_uri)
engine.echo = False
SessionLocal: Session = sessionmaker(bind=engine)
