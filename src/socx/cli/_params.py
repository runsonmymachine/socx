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

configure = partial(
    click.option,
    "--configure/--no-configure",
    type=click.BOOL,
    default=True,
    is_flag=True,
    show_default=True,
    help="whether or not user configurations should be read.",
)

verbosity = partial(
    click.option,
    "-v",
    "--verbosity",
    nargs=1,
    default="INFO",
    show_choices=True,
    show_default=True,
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
    help="Logging verbosity level.",
)
