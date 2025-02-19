import abc
from typing import override
from pathlib import Path
from dataclasses import field
from dataclasses import dataclass

from .log import logger


@dataclass
class Writer[T](abc.ABC):
    """Writes data to a target."""

    @abc.abstractmethod
    def write(self, data: T) -> None:
        """Write data to a target."""
        ...


@dataclass
class FileWriter[T](Writer):
    """
    Writes data to a file.

    Members
    -------
    target: Path
        Target to write to.

    options: dict
        Options for handling write requests.
    """

    target: Path
    options: dict[str, str] = field(default_factory=dict)

    @override
    def write(self, data: str, filename: str) -> None:
        target = Path(self.target)/filename
        if target.exists():
            target.replace(target.with_suffix(".backup"))
        target.write_text(data)

    def __post_init__(self) -> None:
        if not isinstance(self.target, Path):
            self.target = Path(self.target)
        if self.target.exists() and self.target.is_file():
            self._invalid_target_err()
        self.target.mkdir(parents=True, exist_ok=True)

    def _invalid_target_err(self) -> None:
        err = (
            f"Invalid target: '{self.target}'"
            "Target path must point to a directory, not a file."
        )
        exc = ValueError(err)
        logger.exception(err, exc_info=exc)
        raise exc
