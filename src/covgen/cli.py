from __future__ import annotations

from pathlib import Path as Path
from typing import ClassVar as ClassVar
from types import CodeType as CodeType
from types import MethodType as MethodType
from types import MethodWrapperType as MethodWrapperType

import click as click
from .config import settings as settings


class CLI(click.MultiCommand):
    group: ClassVar[MethodWrapperType] = click.Group.group
    command: ClassVar[MethodWrapperType] = click.Group.command

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def plugins_path(self) -> Path:
        return settings.plugins.cli.path

    def list_commands(self, ctx) -> list[str]:
        rv = [
            file.stem
            for file in list(self.plugins_path.rglob("*.py"))
            if file.name != "__init__.py" and file.suffix == ".py"
        ]
        rv.sort()
        return rv

    def get_command(self, ctx, name) -> CodeType:
        ns = {}
        f: Path = Path(self.plugins_path / (name + ".py"))
        code = compile(f.read_text(), f.name, "exec")
        eval(code, ns, ns)
        return ns["cli"]


