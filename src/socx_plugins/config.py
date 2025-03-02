from __future__ import annotations

from contextlib import suppress
from functools import partial
from pathlib import Path

import rich
import rich_click as click
from rich.prompt import Prompt

from socx import console
from socx import settings
from socx import get_logger
from socx import settings_tree


logger = get_logger(__name__)

get_help = f"""
    \n\b
    Print a tree of configurations defined under the field name NAME.
    \n\b
    Possible field names are:
    \b\n{"".join(f"  - {name}\n\b\n" for name in settings.as_dict())}
"""

get_cmd = lambda: partial(  # noqa: E731
    cli.command,
    help=get_help,
    short_help="Print a tree of configurations defined under NAME.",
    no_args_is_help=True,
)()


@click.group("config")
def cli():
    """Get, set, list, or modify settings configuration values."""


@cli.command()
def edit():
    """Edit settings with nano/vim/nvim/gvim."""
    import os
    from socx import APP_SETTINGS_DIR
    from socx import USER_CONFIG_DIR

    files = {Path(name).stem: Path(name) for name in settings.dynaconf_include}
    for file in files.values():
        if not ((path := Path(settings.path_for(file.name))).exists()):
            path = APP_SETTINGS_DIR / file.name
        files[file.stem] = path

    file = files.get(
        Prompt.ask(
            console=console,
            prompt="Which configuration would you like to edit?",
            choices=[Path(file).stem for file in files],
            show_choices=True,
            case_sensitive=True,
        )
    )
    editor = Prompt.ask(
        console=console,
        prompt="Which editor would you like to use?\n\b\n",
        default="vim",
        choices=["nano", "vim", "nvim", "gvim", "neovim", "emacs"],
        show_choices=True,
        show_default=True,
        case_sensitive=False,
    )
    user_file = USER_CONFIG_DIR/file.name
    if (editor := editor.lower()) == "neovim":
        editor = "nvim"
    if text := click.edit(
        env=os.environ,
        text=file.read_text(),
        editor=editor,
        extension=file.suffix,
        require_save=True,
    ):
        user_file.write_text(text, encoding="utf-8")
        logger.info(f"File saved to: {user_file}")


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


@get_cmd()
@click.argument("name", required=True, type=click.STRING)
def get(name: str):
    tree = None
    with suppress(KeyError, AttributeError):
        field = settings[name]
        tree = settings_tree(field, name)
        console.print(tree)
    if not tree:
        console.print(f"No such field: {name}")
        console.print(click.get_current_context().get_help())
