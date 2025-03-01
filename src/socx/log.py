from __future__ import annotations

import os
import logging
from weakref import proxy
from typing import Final, NewType
from pathlib import Path
from functools import wraps

from rich.console import Console
from rich.logging import RichHandler
from click import open_file


__all__ = (
    # Logging
    "log",
    "info",
    "debug",
    "error",
    "fatal",
    "warning",
    "critical",
    "exception",
    "get_level",
    "set_level",
    "get_logger",
    "add_handler",
    "get_handler",
    "has_handlers",
    "remove_handler",
    "get_handler_names",
    "add_filter",
    "remove_filter",
    "is_enabled_for",
    # Types
    "Level",
    # Defaults
    "DEFAULT_LEVEL",
    "DEFAULT_FORMAT",
    "DEFAULT_HANDLERS",
    "DEFAULT_TIME_FORMAT",
)

Level: NewType = NewType("Level", int | str)
"""
Union type definition of `int | str` for annotating level arguments.
"""

DEFAULT_LEVEL: Final[Level] = os.environ.get("SOCX_VERBOSITY", logging.INFO)
"""
Default logger level, a.k.a verbosity.
"""

DEFAULT_FORMAT: Final[str] = os.environ.get("SOCX_LOG_FORMAT", "%(message)s")
"""
Default logger message format.
"""

DEFAULT_TIME_FORMAT: Final[str] = os.environ.get("SOCX_TIME_FORMAT", "[%X]")
"""
Default logger date format logs.
"""

DEFAULT_CHILD_FORMAT: Final[str] = os.environ.get(
    "SOCX_LOG_FORMAT",
    "%(asctime)s %(levelname)5s - %(filename)5s:%(lineno)-4d - %(message)s",
)
"""
Default logger message format.
"""

DEFAULT_CHILD_FORMATTER: Final[str] = logging.Formatter(
    DEFAULT_FORMAT, DEFAULT_TIME_FORMAT
)
"""
Default logger message format.
"""

DEFAULT_HANDLERS: Final[list[logging.Handler]] = [
    RichHandler(
        level=DEFAULT_LEVEL,
        console=Console(tab_size=4, markup=True, force_terminal=True),
        show_time=True,
        show_level=True,
        rich_tracebacks=True,
        omit_repeated_times=False,
        tracebacks_word_wrap=False,
        tracebacks_show_locals=True,
        log_time_format=DEFAULT_TIME_FORMAT,
    ),
]
"""
Default logging handlers of this module's default `logger`.
"""


def _get_file_handler(path: str | Path) -> logging.Handler:
    return RichHandler(
        level=DEFAULT_LEVEL,
        console=Console(
            file=open_file(
                filename=str(path),
                mode="w",
                encoding="utf-8",
                lazy=True,
            ),
            tab_size=4,
            width=110,
        ),
        markup=False,
        show_time=True,
        show_level=True,
        rich_tracebacks=True,
        locals_max_string=None,
        locals_max_length=None,
        tracebacks_theme="monokai",
        omit_repeated_times=False,
        tracebacks_word_wrap=False,
        tracebacks_show_locals=True,
        log_time_format=DEFAULT_TIME_FORMAT,
    )

def _get_logger(*args, **kwargs) -> logging.Logger:
    kwargs.setdefault("level", DEFAULT_LEVEL)
    kwargs.setdefault("format", DEFAULT_FORMAT)
    kwargs.setdefault("datefmt", DEFAULT_TIME_FORMAT)
    kwargs.setdefault("handlers", DEFAULT_HANDLERS)
    logging.basicConfig(*args, **kwargs)
    return logging.getLogger(__package__.partition(".")[0])


logger = _get_logger()
"""
Default logging handler.

Can be used for default logging when no custom behavior is required.

Generally, it is recommended to use the `get_logger` method instead of the
default logger whenever your application requires something a bit more complex
or extensive than a basic write to console functionality.
"""


def get_logger(name: str, filename: str | None = None)-> logging.Logger:
    """
    Get a pretty printing log handler.

    Parameters
    ----------
    name: str
        Name of the logger.

    filename: str
        Specifies that a FileHandler be created, using the specified filename

    Returns
    -------
    A pretty printing logging.Logger instance.

    """
    rv = logger.getChild(name)
    if filename is not None:
        handler = _get_file_handler(filename)
        handler.setFormatter(DEFAULT_CHILD_FORMATTER)
        rv.addHandler(handler)
    return rv


def log(level: Level, msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.log` function."""
    logger.log(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.info` function."""
    logger.info(msg, *args, **kwargs)


def debug(msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.debug` function."""
    logger.debug(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.warning` function."""
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.error` function."""
    logger.error(msg, *args, **kwargs)


def fatal(msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.fatal` function."""
    logger.fatal(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.exception` function."""
    logger.exception(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    """See documentation of builtin `logging.critical` function."""
    logger.critical(msg, *args, **kwargs)


def get_level(logger: logging.Logger) -> str:
    """See documentation of builtin `logging.getLevel` function."""
    return logger.getLevel()


def set_level(level: Level, logger_: logging.Logger | None = None) -> None:
    """See documentation of builtin `logging.setLevel` function."""
    if logger_ is None:
        logger_ = logger
    for child in logger_.getChildren():
        child.setLevel(level)
    logger_.setLevel(level)


def add_filter(filter: logging.Filter) -> None:  # noqa: A002
    """See documentation of builtin `logging.addFilter` function."""
    logger.addFilter(filter)


def remove_filter(filter: logging.Filter) -> None:  # noqa: A002
    """See documentation of builtin `logging.removeFilter` function."""
    logger.removeFilter(filter)


def get_handler(name: str) -> logging.Handler:
    """See documentation of builtin `logging.getHandler` function."""
    return logging.getHandlerByName(name)


def add_handler(handler: logging.Handler) -> None:
    """See documentation of builtin `logging.addHandler` function."""
    logger.addHandler(handler)


def has_handlers() -> None:
    """See documentation of builtin `logging.hasHandler` function."""
    logger.hasHandlers()


def remove_handler(handler: logging.Handler) -> None:
    """See documentation of builtin `logging.removeHandler` function."""
    logger.removeHandler(handler)


def get_handler_names() -> logging.Handlers:
    """See documentation of builtin `logging.getHandlerNames` function."""
    return logging.getHandlerNames()


def is_enabled_for(level: Level) -> bool:
    """See documentation of builtin `logging.isEnabledFor` function."""
    if isinstance(level, str):
        level = logging.getLevelName(level)
    return logger.isEnabledFor(level)


