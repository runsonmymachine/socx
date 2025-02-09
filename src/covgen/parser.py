from __future__ import annotations

__all__ = ("Parser", "LstParser", "parse")


import re as re
import abc as abc
import json as json
import typing as t
import pathlib as pathlib
import dataclasses as dc
from pathlib import Path as Path

import rich as rich
import click as click
from dynaconf.utils.boxing import DynaBox

from .config import settings as settings
from .memory import SymbolTable as SymbolTable
from .memory import RichSymTable as RichSymTable
from .memory import MemorySegment as MemorySegment
from .memory import DynamicSymbol as DynamicSymbol
from .tokenizer import Token as Token
from .tokenizer import Tokenizer as Tokenizer
from .validators import ConverterValidator as ConverterValidator


class Parser(abc.ABC):
    @abc.abstractmethod
    def parse(self) -> None:
        """Start the parser."""
        ...

    @property
    @abc.abstractmethod
    def lang(self) -> DynaBox:
        """Return the 'lang' configuration of the parser's source language."""
        ...

    @property
    @abc.abstractmethod
    def tokens(self) -> dict:
        """
        Return a dictionary mapping between token names to their internal
        representation as object.
        """
        ...


@dc.dataclass
class LstParser(Parser):
    """
    Parses .lst files to functions definitions represented as a
    python object.

    See DynamicSymbol, MemorySegment, RichSymTable.
    """

    options: dict[str, str] | None = None
    includes: set[pathlib.Path] | None = None
    excludes: set[pathlib.Path] | None = None
    source_dir: pathlib.Path | None = None
    target_dir: pathlib.Path | None = None

    def __init__(
        self: t.Self,
        options: dict[str, str] | None = None,
        includes: set[pathlib.Path] | None = None,
        excludes: set[pathlib.Path] | None = None,
        source_dir: pathlib.Path | None = None,
        target_dir: pathlib.Path | None = None,
    ) -> None:
        """
        Initialize the parser.

        Parameters
        ----------
        source_dir
            Source directory from which sources are included and parsed by the
            parser.
        target_dir
            Target directory to which parsed sources will be saved with as
            configured in convert.toml
        options
            Options for handling the conversion operation. See `convert.toml`
            for additional info.
        """
        if options is None:
            options = self.convert.options
        if includes is None:
            includes = self.convert.includes
        if excludes is None:
            excludes = self.convert.excludes
        if source_dir is None:
            source_dir = self.convert.source
        if target_dir is None:
            target_dir = self.convert.target
        self.options = options
        self.includes = set()
        self.excludes = set()
        self.sym_table = RichSymTable()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.includes = ConverterValidator._extract_includes(
            self.source_dir, includes, excludes
        )

    @property
    def cfg(self) -> DynaBox:
        return settings.convert[self.lang]

    @property
    def lang(self) -> DynaBox:
        return "lst"

    @property
    def tokens(self) -> DynaBox:
        return settings.lang[self.lang].tokens

    def parse(self) -> None:
        """Parse the sources according to initialization configuration."""
        for include in self.includes:
            self.tokenize(include)
        self.sym_table.update(self._parse_sym_table())

    def tokenize(self, src: pathlib.Path) -> tuple[Token]:
        text = src.read_text()
        lines = text.splitlines(False)
        tokens = {token.name: token for token in self.tokens}  # noqa: F841
        expr_map = {  # noqa: F841
            token.name: re.compile(token.expr) for token in self.tokens
        }
        pattern = "|".join(
            "(?P<%s>%s)" % (token.name, token.expr) for token in self.tokens
        )
        for line in lines:
            for match in re.finditer(pattern, line):
                if not match:
                    continue
                kind = match.group()
                before = match.string[0 : match.start()]
                matched = match.string[match.start() : match.end()]
                after = match.string[match.end() : :]
                rich.print(f"{kind=}->{before}{matched}{after}")

    def parseone(self, src: Path) -> None:
        pass

    def parse_line(self, line: str) -> None:
        pass

    def _parse_lst_source(self: t.Self, src: pathlib.Path) -> RichSymTable:
        pass

    def _parse_sym_table_funcs(self: t.Self) -> None:
        pass

    def _parse_sym_table(self: t.Self) -> RichSymTable:
        table = RichSymTable()
        memory_map = {}
        base_addr_file = self.convert.base_addr_map
        base_addr_path = pathlib.Path(self.source_dir / base_addr_file)
        field_names = tuple([field.name for field in dc.fields(MemorySegment)])
        base_addr_map = json.loads(base_addr_path.read_text())
        for name in field_names:
            for device_field, value in base_addr_map.items():
                if name not in device_field:
                    continue
                device = str(device_field).removesuffix(f"_{name}")
                if device not in memory_map:
                    memory_map[device] = {}
                memory_map[device][name] = int(
                    value, self.convert.base_addr_base
                )
        table = RichSymTable()
        for device in memory_map:
            if all(name in memory_map[device] for name in field_names):
                space = MemorySegment(**dict(memory_map[device].items()))
                table = RichSymTable(device, space)
                table[device] = (space, None)
        self.sym_table = table
        return table


@click.pass_context
def parse(ctx: click.Context) -> RichSymTable:
    src = ctx.source_dir if hasattr(ctx, "source_dir") else None
    target = ctx.target_dir if hasattr(ctx, "target_dir") else None
    parser = LstParser(src, target)
    parser.parse()
    table = parser.sym_table
    rich.print(parser)
    rich.print(table)
    return table


def write(ctx: click.Context) -> None:
    for asm in ctx.mods:
        output_file = ctx.output / asm.file.with_suffix(".sv")
        output_file.write_text(asm.to_sv())
        print(f"SystemVerilog output successfuly written to {output_file}")
