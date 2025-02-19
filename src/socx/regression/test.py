from __future__ import annotations

import signal
from contextlib import suppress
from typing import TextIO
from enum import auto
from enum import IntEnum
from subprocess import Popen
from subprocess import PIPE
from dataclasses import field
from dataclasses import dataclass


class TestStatus(IntEnum):
    """
    TestStatus representation of a test process as an `IntEnum`.

    Members
    -------
    Idle: IntEnum
        Idle state, awaiting to be started.

    Running: IntEnum
        Test is currently running on a seperate process.

    Passed: IntEnum
        Test has ended with no errors and a clean exit code.

    Failed: IntEnum
        Test had failed due to an error or an invalid exit code.

    Killed: IntEnum
        Test was intentionally killed by a signal.
    """

    Idle = auto(0)
    Running = auto()
    Passed = auto()
    Failed = auto()
    Killed = auto()


@dataclass
class TestCommand:
    """
    Representation of a 'run test' command-line as an object.

    Members
    -------
    line: str
        Full commandline string of the command represented by this object.

    name: str
        Name of the command represented by this object, i.e. sys.argv[0].

    args: list[str]
        Arguments of the command represented by this object split by
        whitespace.
    """

    name: str = field(init=False)
    args: list[str] = field(init=False)
    line: str

    def __getattr__(self, attr: str) -> str:
        v = self.extract_argv(f"--{attr}")
        if v:
            return v
        else:
            raise AttributeError

    def extract_argv(self, arg: str) -> str:
        with suppress(ValueError):
            index = self.args.index(f"{arg}")
            return self.args[index + 1] if index + 1 < len(self.args) else ""
        return ""

    def __post_init__(self) -> None:
        self.line = self.line.strip()
        self.args = [arg.strip() for arg in self.line.split()]
        self.name = self.args[0] if self.args else ""

    def __hash__(self) -> int:
        return hash(self.line)


@dataclass(init=False)
class Test:
    """Representation of a test as a python object."""

    name: str
    flow: str
    seed: int
    status: TestStatus
    command: TestCommand
    process: Popen | None

    def __init__(self, command: str | TestCommand) -> None:
        self._proc = None
        self._command = (
            command
            if isinstance(command, TestCommand)
            else TestCommand(command)
        )

    @property
    def pid(self) -> int | None:
        """Process id of the test's active process or None if inactive."""
        return self.process.pid if self.process else None

    @property
    def name(self) -> str:
        """The test name or empty string if command does not specify a test."""
        test = self.command.test
        if "/" in test:
            test = test.partition("/")[-1]
        return test

    @property
    def flow(self):
        """The flow specified in the test command."""
        return self.command.flow

    @property
    def seed(self):
        """The test seed."""
        with suppress(AttributeError):
            rv = int(self.command.seed)
            return rv
        return 0

    def start(self) -> None:
        """Start a test in a subprocess."""
        if self.idle:
            self._proc = Popen(
                args=self.command.args,
                text=True,
                stdout=PIPE,
                stderr=PIPE,
                shell=True,
            )
        else:
            err = "Test is already running."
            raise OSError(err)

    def stop(self) -> None:
        """Send a keyboard interrupt (SIGINT) to stop a running test."""
        if self.running:
            self.process.send_signal(signal.SIGINT)

    def pause(self) -> None:
        """Pause the process if it is running."""
        if self.running:
            self.process.send_signal(signal.SIGSTOP)

    def resume(self) -> None:
        """Resume the process if it is paused."""
        if self.running:
            self.process.send_signal(signal.SIGCONT)

    def wait(self, timeout: float | None = None) -> None:
        """Wait for a test to terminate if it is running."""
        if self.running:
            self.process.wait()

    def kill(self) -> None:
        """See `subprocess.Popen.kill`."""
        if self.running:
            self.process.kill()

    def terminate(self) -> None:
        """See `subprocess.Popen.terminate`."""
        if self.running:
            self.process.terminate()

    @property
    def process(self) -> Popen | None:
        """The active process of the running test or None if not running."""
        return self._proc

    @property
    def stdin(self) -> TextIO | None:
        """The standard input of the test's process or None if not running."""
        return self.process.stdin if self.process else None

    @property
    def stdout(self) -> TextIO | None:
        """The standard output of the test's process or None if not running."""
        return self.process.stdout if self.process else None

    @property
    def stderr(self) -> TextIO | None:
        """The standard error of the test's process or None if not running."""
        return self.process.stderr if self.process else None

    @property
    def status(self) -> TestStatus:
        """A `TestStatus` representing the state/status of the test."""
        return self._status()

    @property
    def command(self) -> TestCommand:
        """A `TestCommand` represeinting the test's command line invocation."""
        return self._command

    @property
    def returncode(self) -> int | None:
        """The return code from the test process or None if running or idle."""
        return self.process.returncode if self.finished else None

    @property
    def idle(self) -> bool:
        """True if test has no active process and has not yet started."""
        return self.status is TestStatus.Idle

    @property
    def passed(self) -> bool:
        """True if test has finished running and no errors occured."""
        return not self.finished and self.status is TestStatus.Passed

    @property
    def failed(self) -> bool:
        """True if test finished running and at least one error occured."""
        return self.finished and self.status is TestStatus.Failed

    @property
    def running(self) -> bool:
        """True if test is currently running in a dedicated process."""
        return self.process is not None and self.process.poll() is None

    @property
    def finished(self) -> bool:
        """True if test finished running without normally interruption."""
        return self.process is not None and self.process.poll() is not None

    def _status(self) -> TestStatus:
        if self.process is None:
            return TestStatus.Idle
        elif self.stdout.strip().startswith("PPPP"):
            return TestStatus.Passed
        elif self.stdout.strip().startswith("FFFF"):
            return TestStatus.Running
        else:
            return TestStatus.Failed
