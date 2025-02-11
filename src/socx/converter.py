from __future__ import annotations

import abc
from typing import override
from dataclasses import dataclass

from dynaconf.utils.boxing import DynaBox

from .console import console
from .config import settings
from .reader import Reader
from .reader import FileReader
from .writer import Writer
from .writer import FileWriter
from .parser import Parser
from .parser import LstParser
from .tokenizer import Tokenizer
from .tokenizer import LstTokenizer
from .formatter import Formatter
from .formatter import SystemVerilogFormatter


@dataclass(unsafe_hash=True)
class Converter(abc.ABC):
    reader: Reader | None = None
    writer: Writer | None = None
    parser: Parser | None = None
    tokenizer: Tokenizer | None = None
    formatter: Formatter | None = None

    @property
    def cfg(self) -> DynaBox:
        return settings.convert[self.lang]

    @property
    @abc.abstractmethod
    def lang(self) -> DynaBox: ...

    @abc.abstractmethod
    def convert(self) -> None: ...


@dataclass
class LstConverter(Converter):
    def __post_init__(self) -> None:
        self.parser = LstParser()
        self.reader = FileReader(
            self.cfg.source, self.cfg.includes, self.cfg.excludes
        )
        self.writer = FileWriter()
        self.tokenizer = LstTokenizer()
        self.formatter = SystemVerilogFormatter()

    @override
    @property
    def lang(self) -> DynaBox:
        return "lst"

    def convert(self) -> None:
        console.clear()
        inputs = self.reader.read()
        outputs = {path: "" for path in inputs}
        self.parser.parse()
        for path, input_text in inputs.items():
            matches = self.tokenizer.tokenize(input_text)
            outputs[path] = self.formatter.format(
                self.tokenizer.token_map, matches, self.parser.sym_table
            )
            console.rule("Input:")
            console.print(input_text)
            console.rule("Output:")
            console.print(outputs[path])
            console.rule("Symbol Table:")
            console.print(self.parser.sym_table)
            outfile = self.cfg.target / path.with_suffix(".svh").name
            outfile.write_text(outputs[path])
