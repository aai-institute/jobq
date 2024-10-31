import logging
from contextlib import asynccontextmanager

import kubernetes.config
from fastapi import FastAPI, Response
from sqlmodel import select

from jobq_server.config import settings
from jobq_server.db import check_migrations, get_engine, upgrade_migrations
from jobq_server.routers import jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.DEBUG)

    # Check if the database schema is up to date
    needs_migrations = check_migrations()
    if not needs_migrations:
        if settings.AUTO_MIGRATE:
            logging.info("Upgrading database schema")
            upgrade_migrations()
        else:
            logging.error("Database migrations are not up to date. Exiting.")
            raise SystemExit(1)

    kubernetes.config.load_config()

    yield


app = FastAPI(
    title="jobq API",
    description="Backend service API for the jobq workflow engine",
    lifespan=lifespan,
)

app.include_router(jobs.router, prefix="/jobs")


@app.get("/health", include_in_schema=False)
async def health():
    try:
        with get_engine().connect() as conn:
            conn.execute(select(1))
        return {"status": "ok"}
    except Exception:
        logging.error("Database connection failed", exc_info=True)
        return Response(status_code=503)


# URLs to be excluded from Uvicorn access logging
log_exclude_endpoints = ["/health"]


class AccessLogFilter(logging.Filter):
    def filter(self, record):
        if record.args and len(record.args) >= 3:
            if record.args[2] in log_exclude_endpoints:
                return False
        return True


uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(AccessLogFilter())
