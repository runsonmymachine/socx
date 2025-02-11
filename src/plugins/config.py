import sys
from pathlib import Path

import rich
import click
from rich.prompt import Prompt

from socx import (
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


@command("help", parent=cli)
@click.argument("command", required=False, default=None, type=str)
@click.pass_context
def help_(ctx: click.Context, command: str | None = None):
    """Display usage and help information."""
    cmd = cli.get_command(ctx, command) if command else None
    help_text = cmd.get_help(ctx) if cmd else cli.get_help(ctx)
    rule_text = f"{ctx.command_path}{f'->{cmd.name}' if cmd else ''}"
    rule_style = "[magenta on gray30]"
    console.rule(f"{rule_style}{rule_text}", align="center")
    console.print(f"{help_text}")
    console.rule("")


@command(parent=cli)
def inspect():
    """Inspect the current settings instance and print the results."""
    console.clear()
    rich.inspect(settings, console=console, all=True)


@command("list", parent=cli)
def list_():
    """Print a list of all current configuration values."""
    tree = settings_tree(settings)
    console.clear()
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
        console.clear()
        console.print(tree)


@command(parent=cli)
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
