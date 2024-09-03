import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from kubernetes import config
from pydantic import ValidationError

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


@app.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    errors = [{"field": err["loc"][0], "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": {"message": "Validation Error", "details": errors}},
    )


app.include_router(jobs.router)
