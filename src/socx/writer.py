import abc
from typing import override
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Writer[T](abc.ABC):
    """
    Writes data to a target.

    Attributes
    ----------
    target: Path
        Target to write to.

    options: dict
        Options for handling write requests.
    """

    target: Path | None = (None,)
    options: dict[str, str] | None = (None,)

    @abc.abstractmethod
    def write(self, data: T) -> None:
        """Write data to a target."""
        ...


class FileWriter[T](Writer[T]):

    @override
    def write(self, data: T) -> None:
        pass
