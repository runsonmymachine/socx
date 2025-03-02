from functools import partial

import rich_click as click

from . import _cli

socx = partial(
    click.command,
    "socx",
    cls=_cli.CmdLine,
    invoke_without_command=True,
    no_args_is_help=True,
)

help_ = partial(click.help_option, "--help", "-h")

debug = partial(
    click.option,
    "--debug",
    "-d",
    type=click.BOOL,
    default=False,
    is_flag=True,
    envvar="SOCX_DEBUG",
    show_envvar=True,
    show_default=True,
    expose_value=True,
    help="Run in debug mode.",
)

configure = partial(
    click.option,
    "--configure/--no-configure",
    type=click.BOOL,
    default=True,
    is_flag=True,
    envvar="SOCX_VERBOSITY",
    show_envvar=True,
    show_default=True,
    expose_value=True,
    help="Load/Don't-Load local user configuration overrides.",
)

verbosity = partial(
    click.option,
    "-v",
    "--verbosity",
    nargs=1,
    default="INFO",
    type=click.Choice(
        (
            "CRITICAL",
            "FATAL",
            "ERROR",
            "WARNING",
            "WARN",
            "INFO",
            "DEBUG",
        ),
        case_sensitive=False,
    ),
    help="Run with custom logging verbosity level.",
    show_choices=True,
    show_default=True,
)
