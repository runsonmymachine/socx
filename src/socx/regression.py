from __future__ import annotations

import time
import sched
import psutil as ps
import subprocess as subps
from enum import auto
from enum import IntEnum
from typing import TextIO
from typing import Sequence
from pathlib import Path
from subprocess import Popen
from dataclasses import field
from collections.abc import Iterator
from collections.abc import Iterable
from dataclasses import dataclass

from dynaconf.utils.boxing import DynaBox

from .test import Test
from .mixins import UIDMixin 
from .mixins import PtrMixin
from .config import settings
from .visitor import Node
from .visitor import Visitor
from .visitor import Structure


__all__ = ("Status", "Regression")


class RegressionStatus(IntEnum):
    """
    Status representation of a test process as an `IntEnum`.

    Members
    -------
    Idle: IntEnum
        Regression is idle.

    Preparing: IntEnum
        Regression is preparing for a run.

    Running: IntEnum
        Regression session is running.

    Paused: IntEnum
        Regression has been paused and is ready to be continued.

    Stopped: IntEnum
        Regression has been stopped, it cannot be continued and needs to be
        reran, however, its state, logs, and outputs are kept and can be
        inspected at any time (even during/after a rerun).

    Passed: IntEnum
        Regression has passed.

    Failed: IntEnum
        One of the regression phases had failed to complete or returned with
        an error.

    Killed: IntEnum
        Regression was intentionally killed by a signal.

    TimedOut: IntEnum
        Regression was running for longer then the specified timeout and was
        intentionally killed.
    """

    Idle = auto(0)
    Preparing = auto()
    Running = auto()
    Stopped = auto()
    Paused = auto()
    Passed = auto()
    Failed = auto()
    Killed = auto()
    TimedOut = auto()


@dataclass
class Regression(Structure[Test]):
    name: str
    status: list[RegressionStatus]
    options: DynaBox

    def accept(self, visitor: Visitor[Test]):
        visitor.visit(test)

    def __iter__(self) -> Iterator:
        return iter(self.tests)

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
    def status(self) -> Status:
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
