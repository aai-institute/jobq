import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import config

from jobs_server.routers import jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.DEBUG)
    config.load_config()
    yield


app = FastAPI(
    title="infrastructure-product API",
    description="Backend service for the appliedAI infrastructure product",
    lifespan=lifespan,
)

app.include_router(jobs.router, prefix="/jobs")


# CORS

origins = [
    "http://localhost",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


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
