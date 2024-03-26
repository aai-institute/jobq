import functools
import inspect
import os
from typing import Any, Callable


class Job:
    def __init__(self, func: Callable) -> None:
        functools.update_wrapper(self, func)
        self._func = func

        module = inspect.getmodule(self._func)

        self._name = self._func.__name__
        self._file = os.path.relpath(str(module.__file__))

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._func(*args, **kwargs)


job = Job
