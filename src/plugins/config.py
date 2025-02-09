from pathlib import Path

import rich
import click
from rich.prompt import Prompt

from covgen import (
    group,
    command,
    console,
    settings,
    settings_tree,
)


@group("config", plugin=False)
@click.pass_context
def cli(ctx: click.Context):
    """Get, set, list, or modify settings configuration values."""


@command(parent=cli)
def inspect():
    """Inspect the current settings instance and print the results."""
    with console.pager(styles=True, links=True):
        rich.inspect(settings, console=console, all=True)


@command("list", parent=cli)
def list_():
    """Print a list of all current configuration values."""
    tree = settings_tree(settings)
    with console.pager(styles=True, links=True):
        console.print(tree)


@command(parent=cli)
@click.argument("field_name", required=True, type=str)
def get(field_name: str):
    """Print a tree/table/value representation of the settings field."""
    try:
        field = settings[field_name]
        tree = settings_tree(field, field_name)
    except (KeyError, AttributeError):
        console.print(f"No such field: {field_name}")
        console.print(click.get_current_context().get_help())
    else:
        with console.pager(styles=True, links=True):
            console.print(tree)


@command(parent=cli)
def edit():
    """Edit current settings from console using nano/vim/nvim/gvim."""
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


