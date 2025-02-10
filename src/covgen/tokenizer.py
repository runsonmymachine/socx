from __future__ import annotations

import re
import functools
import abc
import typing as t
import dataclasses as dc
from pathlib import Path

from dynaconf.utils.boxing import DynaBox

from .config import settings
from .console import console


class Position(t.NamedTuple):
    line: int
    column: int


class Scope(t.NamedTuple):
    name: str
    expr: str
    subst: str


class Token(t.NamedTuple):
    name: str
    expr: str
    subst: str
    value: str
    starts_scope: bool
    scope_ender: Scope | None = None


@functools.cache
def _token_map(inst: Tokenizer) -> dict[str, Token]:
    # tmap = {}
    # for i, token in enumerate(inst.tokens):
    #     name = token.name
    #     expr = token.expr
    #     subst = token.subst
    #     starts_scope = token.starts_scope
    #     if not starts_scope:
    #         scope_ender = None
    #     else:
    #         endscope = inst.tokens[i][name].endscope
    #         scope_ender = Scope(name, endscope.expr, endscope.subst)
    #     tmap[name] = Token(name, expr, subst, starts_scope, scope_ender)
    return {token.name: token for token in inst.tokens}


class Tokenizer(abc.ABC):
    """docstring for Tokenizer(abc.ABC):."""

    def cfg(self) -> DynaBox:
        return settings.convert[self.lang]

    @property
    def lang(self) -> DynaBox:
        raise NotImplementedError

    @property
    def tokens(self) -> DynaBox:
        return settings.lang[self.lang].tokens

    @property
    def token_map(self) -> dict[str:Token]:
        return _token_map(self)

    @abc.abstractmethod
    def tokenize(self: t.Self, src: Path) -> tuple[re.Match]:
        raise NotImplementedError


@dc.dataclass(unsafe_hash=True)
class LstTokenizer:
    def __post_init__(self) -> None:
        for token in self.tokens:
            if token.starts_scope:
                pass

    @property
    def cfg(self) -> DynaBox:
        return settings.convert[self.lang]

    @property
    def lang(self) -> DynaBox:
        return "lst"

    @property
    def tokens(self) -> DynaBox:
        return settings.lang[self.lang].tokens

    @property
    def token_map(self) -> dict[str:Token]:
        return _token_map(self)

    def tokenize(self, src: Path) -> tuple[re.Match]:
        text = src.read_text()
        lines = text.splitlines(False)
        flags = re.MULTILINE | re.DOTALL | re.VERBOSE
        raw_pattern = "|".join(
            "(?P<%s>%s)" % (token.name, token.expr) for token in self.tokens
        )
        pattern = re.compile(raw_pattern, flags)
        matches = []
        for line in lines:
            matches.extend(match for match in pattern.finditer(line))
        return tuple(matches)

    def print_matches(self, matches: tuple[re.Match]) -> None:
        style_in = "[red]"
        style_out = "[white]"
        style_type = "[magenta]"
        token_map = self.token_map
        started_scope = {
            token.name: False
            for token in self.tokens
            if token.starts_scope is True
        }
        with console.pager(styles=True, links=True):
            console.rule(f"{style_type}Input:")

            for match in matches:
                subst = self.token_map[match.lastgroup].subst
                console.print(f"{style_in}{match.string}")

            console.rule(f"{style_type}Output:")
            for match in matches:
                if token_map[match.lastgroup].starts_scope:
                    if not started_scope[match.lastgroup]:
                        started_scope[match.lastgroup] = True
                    else:
                        console.print(token_map[match.lastgroup].scope_ender)
                subst = self.token_map[match.lastgroup].subst
                console.print(f"{style_out}{match.expand(subst)}")
            for name in started_scope:
                if started_scope[name]:
                    matched = None
                    for match in matches[-1::-1]:
                        if match.lastgroup == name:
                            matched = match
                            break
                    console.print(matched.expand(token_map[name].scope_ender))
