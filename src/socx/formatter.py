import re
import abc
from typing import override
from dataclasses import dataclass

from dynaconf.utils.boxing import DynaBox


@dataclass
class Formatter(abc.ABC):
    @abc.abstractmethod
    def format(
        self, tokens: dict[str, DynaBox], matches: list[re.Match]
    ) -> str:
        """Format matches as text."""
        ...


class SystemVerilogFormatter(Formatter):
    @override
    def format(
        self, tokens: dict[str, DynaBox], matches: list[re.Match]
    ) -> str:
        state = True
        header = ""
        footer = ""
        output = ""
        for match in matches:
            name = match.lastgroup
            tok = tokens[name]
            if tok.starts_scope:
                output += header if state else footer
                state = not state
                header = match.expand(tok.subst)
                footer = match.expand(tok.scope_ender)
            output += match.expand(tok.subst)
        output += footer
        return output
