from __future__ import annotations

import re
import abc
from typing import Self
from typing import override
from dataclasses import dataclass

from dynaconf.utils.boxing import DynaBox

from .config import settings


class Tokenizer(abc.ABC):
    """Convert text to tokens."""

    def __init__(self) -> None:
        self._matchs = {}
        self._token_map = {token.name: token for token in self.tokens}

    @property
    def cfg(self) -> DynaBox:
        return settings.lang.get(self.lang)

    @property
    @abc.abstractmethod
    def lang(self) -> DynaBox: ...

    @property
    def tokens(self) -> DynaBox:
        return self.cfg.tokens

    @property
    def token_map(self) -> dict[str, DynaBox]:
        return self._token_map

    @abc.abstractmethod
    def tokenize(self: Self, text: str) -> tuple[re.Match]: ...


@dataclass(unsafe_hash=True)
class LstTokenizer(Tokenizer):

    def __init__(self) -> None:
        super().__init__()

    @override
    @property
    def lang(self) -> DynaBox:
        return "lst"

    @override
    def tokenize(self, text: str) -> tuple[re.Match]:
        matches = []
        flags = re.MULTILINE | re.DOTALL | re.VERBOSE
        template = "|".join(
            "(?P<%s>%s)" % (token.name, token.expr)
            for token in self.tokens
        )
        pattern = re.compile(template, flags)
        for line in text.splitlines():
            matches.extend(match for match in pattern.finditer(line))
        return tuple(matches)
