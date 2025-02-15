from weakref import proxy

from rich import pretty
from rich.console import Console

__all__ = ("console",)

_console: Console = Console(record=True, tab_size=4)
pretty.install(_console, overflow="ignore", indent_guides=True, max_length=78)
console = proxy(_console)
