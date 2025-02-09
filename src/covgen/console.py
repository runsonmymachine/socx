import weakref

from rich import pretty
from rich.console import Console

__all__ = ("console",)

_console: Console = Console(record=True, tab_size=4)
pretty.install(None, overflow="fold", indent_guides=True, max_length=78)
pretty.install(_console, overflow="fold", indent_guides=True, max_length=78)
console = weakref.proxy(_console)
