from __future__ import annotations


import os
import logging
from weakref import proxy
from typing import Final, NewType
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from click import open_file


__all__ = (
    # API
    "log",
    "info",
    "warn",
    "error",
    "fatal",
    "debug",
    "warning",
    "exception",
    "critical",
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
        rich_tracebacks=False,
        omit_repeated_times=False,
        tracebacks_word_wrap=False,
        tracebacks_show_locals=False,
        log_time_format=DEFAULT_TIME_FORMAT,
        tracebacks_theme="monokai",
        locals_max_string=None,
        locals_max_length=None,
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

def _get_logger() -> logging.Logger:
    logging.basicConfig(
        level=DEFAULT_LEVEL,
        format=DEFAULT_FORMAT,
        datefmt=DEFAULT_TIME_FORMAT,
        handlers=DEFAULT_HANDLERS,
    )
    return logging.getLogger(__package__.partition(".")[0])


_logger = _get_logger()


def get_logger(name: str, filename: str | None = None) -> logging.Logger:
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
    rv = _logger.getChild(name)
    if filename is not None:
        handler = _get_file_handler(filename)
        handler.setFormatter(DEFAULT_CHILD_FORMATTER)
        rv.addHandler(handler)
    return rv


def log(level: Level, msg: str, *args, **kwargs) -> None:
    _logger.log(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    _logger.info(msg, *args, **kwargs)


def warn(msg: str, *args, **kwargs) -> None:
    _logger.warn(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    _logger.error(msg, *args, **kwargs)


def fatal(msg: str, *args, **kwargs) -> None:
    _logger.fatal(msg, *args, **kwargs)


def debug(msg: str, *args, **kwargs) -> None:
    _logger.debug(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    _logger.warning(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs) -> None:
    _logger.exception(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    _logger.critical(msg, *args, **kwargs)


def get_level() -> str:
    return _logger.getEffectiveLevel()


def set_level(level: Level) -> None:
    _logger.setLevel(level)


def has_handlers() -> None:
    _logger.hasHandlers()


def add_handler(handler: logging.Handler) -> None:
    _logger.addHandler(handler)


def get_handler(name: str) -> logging.Handler:
    return logging.getHandlerByName(name)


def remove_handler(handler: logging.Handler) -> None:
    _logger.removeHandler(handler)


def get_handler_names() -> logging.Handlers:
    return logging.getHandlerNames()


def add_filter(filter: logging.Filter) -> None:  # noqa: A002
    _logger.addFilter(filter)


def remove_filter(filter: logging.Filter) -> None:  # noqa: A002
    _logger.removeFilter(filter)


def is_enabled_for(level: Level) -> bool:
    if isinstance(level, str):
        level = logging.getLevelName(level)
    return _logger.isEnabledFor(level)

logger = proxy(_logger)
"""
Default logging handler.

Can be used for default logging when no custom behavior is required.

If custom logging is needed, use `get_logger` method to get a custom handler
instead.
"""
