import abc
from typing import override
from pathlib import Path
from dataclasses import dataclass

from .validators import PathValidator


@dataclass
class Reader(abc.ABC):
    """
    Reads input from one or more sources.

    Attributes
    ----------
    source: Path
        Source of input to read from.

    includes: set[Path]
        Names or patterns to include in the reading list.

    exludes: set[Path]
        Names or patterns to exclude from the reading list.
    """

    source: Path | None = None
    includes: set[Path] | None = None
    excludes: set[Path] | None = None

    @abc.abstractmethod
    def read(self) -> dict[Path, str]:
        """Read text from one or more sources into a dictionary."""
        ...


@dataclass
class FileReader(Reader):
    @override
    def read(self) -> dict[Path, str]:
        return {path: path.read_text() for path in self.paths}

    @property
    def paths(self) -> set[Path]:
        return PathValidator._extract_includes(
            src=self.source, includes=self.includes, excludes=self.excludes
        )

