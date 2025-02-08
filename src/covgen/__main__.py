import rich as rich
import click as click
import dynaconf as dynaconf

from .cli import CLI as CLI
from .parser import parse as parse
from .console import console as console
from ._options import input_ as input_
from ._options import output as output
from ._options import indent as indent
from .config import settings as settings


@click.group("covgen", invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context):
    """Convert lst files to SystemVerilog covergroups."""


@click.group(cls=CLI, invoke_without_command=True)
@click.pass_context
def plugins(ctx: click.Context) -> None:
    """Run custom command line interface plugins written by users."""


@cli.command("help")
@click.help_option("-h", "--help", show_choices=True, show_default=True)
@click.pass_context
def help_(ctx: click.Context) -> None:
    """Get command usage and help information."""
    click.echo(cli.get_help(ctx))


@cli.group()
@click.pass_context
def config(ctx: click.Context):
    """Set, get, or execute configuration related operations."""


@cli.command()
@click.pass_context
def convert(ctx: click.Context):
    """Perform a conversion based on current configurations."""
    ctx.invoke(parse)


@config.command("list")
@click.pass_context
def config_list(ctx: click.Context):
    """Print a list of all current configuration values."""
    rich.inspect(
        settings.as_dict(),
        title="Settings",
        sort=False,
        help=False,
        docs=False,
        value=True,
    )


cli = click.CommandCollection(sources=[cli, plugins])


if __name__ == "__main__":
    cli(obj={})
