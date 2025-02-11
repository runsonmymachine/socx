from __future__ import annotations

from types import CodeType
from typing import Self
from typing import Iterator
from pathlib import Path
from functools import wraps

import click

from .log import log
from .config import settings
from .console import console


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class CLIPlugin(click.Group):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        name = args[0] if args else kwargs.get("name")
        log.debug(f"Plugin {name} created.")

    def __iter__(self) -> Iterator:
        ctx = click.get_current_context()
        return iter(self.list_commands(ctx))

    @property
    def plug_name(self) -> str:
        if self.name in ["cli", "plugins"]:
            return "plugins"
        return self.name

    @property
    def plug_path(self) -> Path:
        return self.plug_settings.path

    @property
    def plug_settings(self) -> dict:
        if self.plug_name in ["cli", "plugins"]:
            return settings.plugins
        else:
            return settings.plugins.get(self.plug_name)

    def list_commands(self, ctx) -> list[str]:
        commands = list(self.commands.keys())
        for path in self.plug_path.glob("**/*.py"):
            parent = path.parent
            if path.name == "__init__.py" and parent.name != self.plug_name:
                commands.append(parent.name)
            elif path.name != "__init__.py" and parent.name == self.plug_name:
                commands.append(path.stem)
        commands.sort()
        return commands

    def get_command(self, ctx: click.Context, name: str) -> CodeType:
        def _compile(file, name):
            ns = {}
            code = compile(file.read_text(), name, "exec")
            eval(code, ns, ns)
            return ns.get("cli")

        if name in self.commands:
            return self.commands[name]
        for file in self.plug_path.glob(f"**/{name}.py"):
            if file.parent.name == self.plug_name and file.stem == name:
                return _compile(file, file.name)
        for file in self.plug_path.glob("**/__init__.py"):
            if file.parent.name != self.plug_name and file.parent.name == name:
                return _compile(file, file.name)
        return None


def group(*args, plugin: bool = True, parent: click.Group = None, **kwargs):
    if plugin and "cls" not in kwargs:
        kwargs["cls"] = CLIPlugin

    if "no_args_is_help" not in kwargs:
        kwargs["no_args_is_help"] = True

    if "context_settings" not in kwargs:
        kwargs["context_settings"] = CONTEXT_SETTINGS

    if parent is None:
        return click.group(*args, **kwargs)

    return parent.group(*args, **kwargs)


def command(*args, parent: click.Group | None = None, **kwargs):
    if parent is None:
        return click.command(
            *args, context_settings=CONTEXT_SETTINGS, **kwargs
        )
    else:
        return parent.command(
            *args, context_settings=CONTEXT_SETTINGS, **kwargs
        )


@group(invoke_without_command=True)
def cli():
    """SoC team tool executer and plugin manager."""

