import logging

from sqlmodel import SQLModel, create_engine

from jobq_server.config import settings

connect_args = {"check_same_thread": False}
engine = create_engine(settings.DB_DSN, connect_args=connect_args)


def create_db_and_tables():
    logging.debug("Creating database and tables, %s", str(engine))
    SQLModel.metadata.create_all(engine)
