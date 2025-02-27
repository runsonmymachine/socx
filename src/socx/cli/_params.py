from functools import partial
import rich_click as click

from ._cli import CmdLine

socx = partial(
    click.group,
    "socx",
    cls=CmdLine
)

help_ = partial(
    click.help_option,
    "-?", "-h", "--help"
)

configure = partial(
    click.option,
    "--configure/--no-configure",
    default=True,
    show_default=True,
    help="whether or not user configurations should be read.",
)

verbosity = partial(
    click.option,
    "-v",
    "--verbosity",
    nargs=1,
    default="INFO",
    show_default=True,
    type=click.Choice(
        [
            "CRITICAL",
            "FATAL",
            "ERROR",
            "WARNING",
            "WARN",
            "INFO",
            "DEBUG",
        ],
        case_sensitive=False,
    ),
    help="Logging verbosity level.",
)
