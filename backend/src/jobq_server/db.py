from threading import Lock

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine
from sqlmodel import create_engine

from jobq_server.config import settings

connect_args = {"check_same_thread": False}

_engine: Engine | None = None
engine_lock = Lock()


def get_engine() -> Engine:
    global _engine

    # Double-checked locking pattern
    if _engine is None:
        with engine_lock:
            if _engine is None:
                _engine = create_engine(
                    settings.DB_CONNECTION_STRING,
                    connect_args=connect_args,
                )
    return _engine


def check_migrations() -> bool:
    """
    Check if the database is up to date with the migration scripts
    """

    # Get the latest available revision from migration scripts
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    # Get the current revision from the database
    with get_engine().connect() as conn:
        context = MigrationContext.configure(conn)
        return set(context.get_current_heads()) == set(script.get_heads())


def upgrade_migrations():
    """Perform a migration upgrade to the latest version"""

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
