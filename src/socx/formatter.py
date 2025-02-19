import re
import abc
from typing import override
from dataclasses import dataclass
from jinja2 import Environment

from dynaconf.utils.boxing import DynaBox

from .parser import SymbolTable


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
        self,
        tokens: dict[str, DynaBox],
        matches: list[re.Match],
        sym_table: SymbolTable,
    ) -> str:
        state = True
        env = Environment()
        base = None
        scope = None
        header = ""
        footer = ""
        output = ""

        for match in matches:
            name = match.lastgroup
            tok = tokens[name]

            if tok.starts_scope:
                output += header if state else footer
                scope = match.expand(r"\g<device>_\g<mem>")
                header = match.expand(tok.subst)
                footer = match.expand(tok.scope_ender)
                if scope and base and not state:
                    template = env.from_string(output)
                    output = template.render(base=base)
                state = not state
                base = None

            if base is None:
                base = match.group("addr")

            output += match.expand(tok.subst)

        output += footer
        template = env.from_string(output)
        output = template.render(base=base)
        return output
