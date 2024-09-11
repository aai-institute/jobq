from inspect import signature

from fastapi import HTTPException
from pydantic import ValidationError


def make_dependable(cls):
    """
    Pydantic BaseModels are very powerful because we get lots of validations and type checking right out of the box.
    FastAPI can accept a BaseModel as a route Dependency and it will automatically handle things like documentation
    and error handling. However, if we define custom validators then the errors they raise are not handled, leading
    to HTTP 500's being returned.

    To better understand this issue, you can visit https://github.com/tiangolo/fastapi/issues/1474 for context.
    A workaround proposed there adds a classmethod which attempts to init the BaseModel and handles formatting of
    any raised ValidationErrors, custom or otherwise. However, this means essentially duplicating the class's
    signature. This function automates the creation of a workaround method with a matching signature so that you
    can avoid code duplication.

    usage:
    async def fetch(thing_request: Annotated[ThingRequest, Depends(make_dependable(ThingRequest))]): ...

    Source: https://github.com/fastapi/fastapi/discussions/9071#discussioncomment-6602497
    """

    def init_cls_and_handle_errors(*args, **kwargs):
        try:
            signature(init_cls_and_handle_errors).bind(*args, **kwargs)
            return cls(*args, **kwargs)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                error["loc"] = ["query"] + list(error["loc"])
                error["ctx"]["error"] = str(error["ctx"]["error"])
                errors.append(error)
            raise HTTPException(
                status_code=422,
                detail=errors,
            ) from e

    init_cls_and_handle_errors.__signature__ = signature(cls)
    return init_cls_and_handle_errors
