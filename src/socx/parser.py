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

from .console import console as console
from .config import settings as settings
from .memory import SymbolTable as SymbolTable
from .memory import MemorySegment as MemorySegment
from .memory import DynamicSymbol as DynamicSymbol
from .tokenizer import Tokenizer as Tokenizer
from .tokenizer import LstTokenizer as LstTokenizer
from .validators import PathValidator as PathValidator


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


@dc.dataclass
class LstParser(Parser):
    """
    Parses .lst files to functions definitions represented as a
    python object.

    See DynamicSymbol, MemorySegment, SymbolTable.
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
            options = self.cfg.options
        if includes is None:
            includes = self.cfg.includes
        if excludes is None:
            excludes = self.cfg.excludes
        if source_dir is None:
            source_dir = self.cfg.source
        if target_dir is None:
            target_dir = self.cfg.target
        self.options = options
        self.includes = includes
        self.excludes = excludes
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.includes = PathValidator._extract_includes(
            self.source_dir, includes, excludes
        )
        self.sym_table = SymbolTable()

    @property
    def cfg(self) -> DynaBox:
        return settings.convert[self.lang]

    @property
    def lang(self) -> DynaBox:
        return "lst"

    def parse(self) -> None:
        """Parse the sources according to initialization configuration."""
        self._parse_sym_table()

    def _parse_sym_table(self: t.Self) -> SymbolTable:
        memory_map = {}
        base_addr_file = self.cfg.base_addr_map
        base_addr_path = pathlib.Path(self.source_dir) / base_addr_file
        field_names = tuple([field.name for field in dc.fields(MemorySegment)])
        base_addr_map = json.loads(base_addr_path.read_text())
        for name in field_names:
            for device_field, value in base_addr_map.items():
                if name not in device_field:
                    continue
                device = str(device_field).removesuffix(f"_{name}")
                if device not in memory_map:
                    memory_map[device] = {}
                memory_map[device][name] = int(value, self.cfg.base_addr_base)
        self.sym_table.clear()
        for device in memory_map:
            if all(name in memory_map[device] for name in field_names):
                space = MemorySegment(**dict(memory_map[device].items()))
                self.sym_table[device] = (space, None)
        self.sym_table = self.sym_table
        return self.sym_table

    def __hash__(self) -> int:
        return hash(tuple(self.includes))
