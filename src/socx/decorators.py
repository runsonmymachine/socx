from inspect import getmodule
from inspect import signature
from functools import wraps
from functools import cache

from .log import get_logger
from ._config import USER_LOG_DIR


__all__ = ("log_it", )


_loggers = {}


def log_it(f):
    """Add automatic debug information logging to decorated functions/methods.

    Apply this decorator to any function or method to add automatic logging
    of debug information for every invocation of the decorated function/method.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        @cache
        def logger(f):
            mod = getmodule(f).__name__
            return get_logger(mod, USER_LOG_DIR/mod)
        sig = f"{f.__name__}{signature(f)}"
        logger(f).debug(f"{sig}: entered.")
        rv = f(*args, **kwargs)
        logger(f).debug(f"{sig}: returned {rv=}.")
        return rv

    return wrapper


