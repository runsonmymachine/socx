__all__ = (
    "console",
)


import typing as t
from rich.console import Console as Console


console: t.Final[Console] = Console(record=True)

