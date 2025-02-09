from __future__ import annotations

import abc as abc
import typing as t
import dataclasses as dc
from pathlib import Path as Path

import rich as rich
import click as click


class Position(t.NamedTuple):
    line: int
    column: int


class Token(t.NamedTuple):
    name: str
    expr: str
    subst: str
    value: str


class Tokenizer(abc.ABC):
    """docstring for Tokenizer(abc.ABC):."""

    @abc.abstractmethod
    def tokenize(self: t.Self, src: Path) -> list[Token]:
        raise NotImplementedError


@dc.dataclass
class LstTokenizer:
    tokens: list[Token] = dc.field(default_factory=list, init=False)

    def tokenize(self, src: Path) -> list[Token]:
        pass
