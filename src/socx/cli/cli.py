from __future__ import annotations

import rich_click as click
from trogon import tui

from . import _cli
from . import _params
from .. import log
from ..config import USER_CONFIG_DIR
from ..config import reconfigure


@tui()
@click.group()
def socx():
    cli()


click.group("socx_plugins", cls=_cli.CmdLine)
@_params.socx()
@_params.configure()
@_params.verbosity()
def cli(configure: bool, verbosity: log.Level) -> None:
    """SoC team tool executer and plugin manager."""
    if configure:
        reconfigure(USER_CONFIG_DIR/"*.toml", [], ["*.toml"])
    log.set_level(verbosity)
