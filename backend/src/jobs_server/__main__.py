import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
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

app.include_router(jobs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
