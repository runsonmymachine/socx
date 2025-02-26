from pathlib import Path
from contextlib import suppress

import rich
import rich_click as click
from rich.prompt import Prompt

from socx import logger
from socx import console
from socx import settings
from socx import settings_tree


@click.group("config")
@click.pass_context
def cli(ctx: click.Context):
    """Get, set, list, or modify settings configuration values."""


@cli.command()
def inspect():
    """Inspect the current settings instance and print the results."""
    console.clear()
    rich.inspect(settings, console=console, all=True)


@cli.command("list")
def list_():
    """Print a list of all current configuration values."""
    console.print(settings.as_dict())


@cli.command("tree")
def tree_():
    """Print a tree of all loaded configurations."""
    tree = settings_tree(settings)
    console.print(tree)


@cli.command()
@click.argument("name", required=True, type=str)
def get(name: str):
    """Print a tree/table/value representation of the settings field."""
    tree = None
    with suppress(KeyError, AttributeError):
        field = settings[name]
        tree = settings_tree(field, name)
        console.print(tree)
    if not tree:
        console.print(f"No such field: {name}")
        console.print(click.get_current_context().get_help())


@cli.command("set")
@click.argument("name", required=True, type=str)
@click.argument("value", required=True, type=str)
def set_(name: str, value: str):
    """Print a tree/table/value representation of the settings field."""
    logger.debug(f"settings update: '{name}={value}'")
    settings.update({name: value}, validate_on_update=True)


@cli.command()
def edit():
    """Edit settings from console using nano/vim/nvim/gvim (interactive)."""
    help_text = """[magenta on gray23]

    You may hit [u]<Ctrl-C>[/u] at any time to abort.

    When inside an editor, [u]close it without saving to abort[/u].[/magenta
    on gray23]
    """
    console.clear()
    console.line(2)
    console.rule("Edit")
    console.line(1)
    console.print(help_text, justify="center")
    console.line(1)
    file = Prompt.ask(
        console=console,
        prompt="Which configuration would you like to edit?",
        choices=[Path(file).name for file in settings.settings_file],
    )
    editor = Prompt.ask(
        console=console,
        prompt="Which editor would you like to use?",
        choices=["nano", "vim", "nvim", "gvim"],
        default="vim",
    )
    file = Path(settings.path_for(file))
    click.edit(filename=str(file), editor=editor, require_save=True)
