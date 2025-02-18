from rich import pretty
from rich.console import Console

__all__ = ("console",)

_console: Console = Console(record=True, tab_size=4, force_terminal=True)
pretty.install(_console, overflow="ignore", indent_guides=True, max_length=78)
console = _console
