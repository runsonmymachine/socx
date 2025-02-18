from __future__ import annotations

import signal
from enum import auto
from enum import IntEnum
from typing import TextIO
from pathlib import Path
from contextlib import suppress
from subprocess import PIPE
from subprocess import Popen
from dataclasses import field
from dataclasses import dataclass

from dynaconf.utils.boxing import DynaBox

from .. import visitor
from .test import Test
from .test import TestStatus
from .test import TestCommand
from ..config import settings


@dataclass(init=False)
class Regression:
    uid: int
    name: str
    log: Path
    tests: list[Test]
    status: list[TestStatus]
    options: DynaBox
    test_logs: list[Path]

    def start(self) -> None:
        """Start a test in a subprocess."""
        pass

    def stop(self) -> None:
        """Send a keyboard interrupt (SIGINT) to stop a running test."""
        pass

    def pause(self) -> None:
        """Pause the process if it is running."""
        pass

    def resume(self) -> None:
        """Resume the process if it is paused."""
        pass

    def wait(self, timeout: float | None = None) -> None:
        """Wait for a test to terminate if it is running."""
        pass

    def kill(self) -> None:
        """See `subprocess.Popen.kill`."""
        pass

    def export(self, fmt: str = "csv") -> None:
        """Export regression sessions to the specified format `fmt`."""
        pass

    def terminate(self) -> None:
        """See `subprocess.Popen.terminate`."""
        pass

    @property
    def log(self) -> Path:
        pass

    @property
    def options(self) -> DynaBox:
        return settings.regression

    @property
    def process(self) -> Popen | None:
        """The active process of the running test or None if not running."""
        pass

    @property
    def stdin(self) -> TextIO | None:
        """The standard input of the test's process or None if not running."""
        pass

    @property
    def stdout(self) -> TextIO | None:
        """The standard output of the test's process or None if not running."""
        pass

    @property
    def stderr(self) -> TextIO | None:
        """The standard error of the test's process or None if not running."""
        pass

    @property
    def status(self) -> TestStatus:
        """A `TestStatus` representing the state/status of the test."""
        pass

    @property
    def test_logs(self) -> dict[str, Path]:
        """Return a mapping between test names and their log paths."""
        pass

    @property
    def idle(self) -> bool:
        """True if test has no active process and has not yet started."""
        pass

    @property
    def passed(self) -> bool:
        """True if test has finished running and no errors occured."""
        pass

    @property
    def failed(self) -> bool:
        """True if test finished running and at least one error occured."""
        pass

    @property
    def running(self) -> bool:
        """True if test is currently running in a dedicated process."""
        pass

    @property
    def finished(self) -> bool:
        """True if test finished running without normally interruption."""
        pass

    @property
    def returncode(self) -> int | None:
        """The return code from the test process or None if running or idle."""
        pass

