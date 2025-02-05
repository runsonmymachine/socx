from __future__ import annotations

import types as types
import functools as fun
import pathlib as pathlib

import rich as rich
import click as click
import dynaconf as dynaconf

from . import parser as parser
from . import options as options
from .config import settings as settings


__all__ = ("covgen",)


class CLI(click.MultiCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def list_commands(self, ctx) -> list[str]:
        rv = []
        plugins: pathlib.Path = pathlib.Path(settings.plugins.path)
        for file in list(plugins.rglob("*.py")):
            name = file.name.split('.')[0] if file.suffix else file.name
            if file.suffix == '.py' and name != '__init__':
                rv.append(name)
        rv.sort()
        return rv

    def get_command(self, ctx, name) -> types.CodeType:
        ns = {}
        f: pathlib.Path = pathlib.Path(settings.plugins.path / (name + '.py'))
        code = compile(f.read_text(), f.name, 'exec')
        eval(code, ns, ns)
        return ns['cli']


@click.group("covgen", invoke_without_command=True)
@click.pass_context
def covgen(ctx: click.Context):
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


@covgen.group("help")
@click.pass_context
def help_(ctx):
    ctx.get_help()



@click.group(cls=CLI, invoke_without_command=True)
@click.pass_context
def plug(ctx: click.Context):
    pass


@covgen.group("config")
@click.pass_context
def config(ctx: click.Context):
    pass


@covgen.command("convert")
@click.pass_context
def convert(ctx: click.Context):
    sym_table = ctx.invoke(parser.parse)


@config.command("list")
@click.pass_context
def list_config(ctx: click.Context):
    rich.inspect(
        settings.as_dict(),
        title="Settings",
        sort=False,
        help=False,
        docs=False,
        value=True,
    )


covgen = click.CommandCollection(sources=[covgen, plug])

