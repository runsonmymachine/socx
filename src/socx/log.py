__all__ = (
    "log",
    "get_logger",
    "DEFAULT_FORMAT",
    "DEFAULT_DATE_FORMAT",
    "DEFAULT_FORMAT_SHORT",
)

from weakref import proxy

import logging
from rich.logging import RichHandler


DEFAULT_FORMAT = "%(asctime)-15s - %(levelname)s - %(message)s"
"""Default logger message format."""

DEFAULT_FORMAT_SHORT = "%(message)s"
"""Default logger short message format."""

DEFAULT_DATE_FORMAT = "[%X]"
"""Default logger date format logs."""


def _get_logger(
    lvl: int = logging.INFO,
    fmt: str = DEFAULT_FORMAT,
    datefmt: str = DEFAULT_DATE_FORMAT,
) -> logging.Logger:
    logging.basicConfig(
        level=lvl,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)
        ],
    )
    return logging.getLogger("rich")


_log = _get_logger()


def get_logger(
    lvl: int = logging.INFO,
    fmt: str = DEFAULT_FORMAT,
    datefmt: str = DEFAULT_DATE_FORMAT,
) -> logging.Logger:
    """
    Get a pretty printing log handler.

    Return a `logging.Logger` instance of type `rich.RichHandler` configured
    to the specified verbosity level `lvl`, message format `fmt`, and date
    format `datefmt`.

    Parameters
    ----------
    lvl: int
        The handler's minimum logging verbosity level.

    fmt: str
        The handler's default message format.

    datefmt: str
        The handler's default date format.

    Returns
    -------
    A `logging.Logger` handler instance of type `rich.RichHandler` configured
    with the specified option arguments.
    """
    return _get_logger(lvl, fmt, datefmt)


log = proxy(_log)
"""
Default logging handler.

Can be used for default logging when no custom behavior is required.

If custom logging is needed, use `get_logger` method to get a custom handler
instead.
"""
