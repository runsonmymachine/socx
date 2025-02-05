from __future__ import annotations

__all__ = ("Parser", "LstFuncParser", "parse")

import abc as abc
import json as json
import typing as t
import pathlib as pathlib
import dataclasses as dc

import rich as rich
import click as click

from .config import settings as settings
from .memory import SymbolTable as SymbolTable
from .memory import AddressSpace as AddressSpace
from .memory import DynamicSymbol as DynamicSymbol
from .validators import ConverterValidator as Validator


class Parser[T](abc.ABC):
    @abc.abstractmethod
    def parse(self) -> T: ...


@dc.dataclass
class LstFuncParser(Parser[SymbolTable]):
    """
    Parses .lst files to functions definitions represented as a
    python object.

    See DynamicSymbol, AddressSpace, SymbolTable.
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
            configured in converter.toml
        options
            Options for handling the conversion operation. See `converter.toml`
            for additional info.
        """
        if options is None:
            options = settings.converter.options
        if includes is None:
            includes = settings.converter.includes
        if excludes is None:
            excludes = settings.converter.excludes
        if source_dir is None:
            source_dir = settings.converter.source
        if target_dir is None:
            target_dir = settings.converter.target
        self.options = options
        self.includes = set()
        self.excludes = set()
        self.sym_table = SymbolTable()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.includes = Validator._extract_includes(self.source_dir, includes, excludes)

    def parse(self) -> None:
        """Parse the sources according to initialization configuration."""
        self._prepare()
        self.sym_table.update(self._parse_sym_table())

    def _prepare(self) -> None:
        self.target_dir.mkdir(exist_ok=True)

    def _parse_sym_table_funcs(self: t.Self) -> None:
        pass
        # for file in self.includes:

    def _parse_sym_table(self: t.Self) -> SymbolTable:
        table = SymbolTable()
        memory_map = {}
        base_addr_file = settings.converter.base_addr_map
        base_addr_path = pathlib.Path(self.source_dir / base_addr_file)
        field_names = tuple([field.name for field in dc.fields(AddressSpace)])
        base_addr_map = json.loads(base_addr_path.read_text())
        for name in field_names:
            for device_field, value in base_addr_map.items():
                if name not in device_field:
                    continue
                device = str(device_field).removesuffix(f"_{name}")
                if device not in memory_map:
                    memory_map[device] = {}
                memory_map[device][name] = int(
                    value, settings.converter.base_addr_base
                )
        table = SymbolTable()
        for device in memory_map:
            if all(name in memory_map[device] for name in field_names):
                space = AddressSpace(**dict(memory_map[device].items()))
                table[device] = (space, None)
        self.sym_table = table
        return table


@click.pass_context
def parse(ctx: click.Context) -> SymbolTable:
    src = ctx.source_dir if hasattr(ctx, "source_dir") else None
    target = ctx.target_dir if hasattr(ctx, "target_dir") else None
    parser = LstFuncParser(src, target)
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
