from __future__ import annotations

import logging

import rich_click as click
from trogon import tui

from . import _params
from ..log import Level
from ..config import reconfigure
from ..config import USER_CONFIG_DIR


@tui()
@_params.socx()
@_params.debug()
@_params.verbosity()
@_params.configure()
def cli(verbosity: Level, configure: bool, debug: bool) -> None:
    """System on chip verification and tooling infrastructure."""
    ctx = click.get_current_context()
    ctx.debug = debug
    ctx.verbosity = verbosity
    mapping = logging.getLevelNamesMapping()
    level = mapping[verbosity.upper()]
    logging.disable(level-(logging.DEBUG-logging.NOTSET))
    if configure:
        reconfigure(USER_CONFIG_DIR / "*.toml", [], ["*.toml"])
    if ctx.invoked_subcommand is None:
        formatter = ctx.make_formatter()
        cli.format_help(ctx, formatter)
