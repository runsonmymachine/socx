from __future__ import annotations

import abc
import shlex
import asyncio as aio
import time
import psutil as ps
from enum import auto
from enum import IntEnum
from typing import TextIO
from typing import override
from contextlib import suppress
from subprocess import PIPE
from dataclasses import field
from dataclasses import dataclass

from .log import logger
from .mixins import UIDMixin
from .visitor import Node
from .visitor import Visitor


@dataclass
class TestCommand(UIDMixin):
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

    line: str
    name: str = field(init=False)
    args: tuple[str] = field(init=False)
    escaped: str = field(init=False)

    def __post_init__(self) -> None:
        self.line = self.line.strip()
        self.args = tuple(arg.strip() for arg in self.line.split())
        self.name = self.args[0] if self.args else ""
        self.escaped = shlex.quote(self.line)

    def extract_argv(self, arg: str) -> str:
        with suppress(ValueError):
            index = self.args.index(f"{arg}")
            return self.args[index + 1] if index + 1 < len(self.args) else ""
        return ""

    def __getattr__(self, attr: str) -> str:
        v = self.extract_argv(f"--{attr}")
        if v:
            return v
        else:
            raise AttributeError

    def __hash__(self) -> int:
        return hash(self.line)


class TestStatus(IntEnum):
    """
    TestStatus representation of a test process as an `IntEnum`.

    Members
    -------
    Idle: IntEnum
        Idle, waiting to be started.

    Running: IntEnum
        Test is running.

    Stopped: IntEnum
        Test has been stopped intentionaly.

    Finished: IntEnum
        Test had finished running normally with an exit code 0.

    Terminated: IntEnum
        Test was intentionally terminated by a signal.
    """

    Idle = auto(0)
    Running = auto()
    Stopped = auto()
    Finished = auto()
    Terminated = auto()


class TestResult(IntEnum):
    """
    Represents the result of a test that had finished and exited normally.

    Members
    -------
    NA: TestResult
        Test has not yet finished running and therefore result is
        non-applicable.

    Passed: TestResult
        Test had finished and terminated normally with no errors and a 0 exit
        code.

    Failed: TestResult
        Test had finished either normally or abnormally with a non-zero exit
        code.
    """

    NA = auto()
    Passed = auto()
    Failed = auto()


@dataclass(init=False)
class TestBase:
    """Definition of basic properties common accross all test types."""

    name: str
    status: TestStatus
    result: TestResult
    command: TestCommand
    end_time: time.time
    start_time: time.time
    elapsed_time: time.time

    def __init__(self, command: str | TestCommand | None = None, *args, **kwargs) -> None:
        if command is None:
            command = TestCommand("")
        elif isinstance(command, str):
            command = TestCommand(command)
        try:
            self._name = command.name
        except AttributeError:
            raise
        self._result = TestResult.NA
        self._status = TestStatus.Idle
        self._command = command
        self._end_time = None
        self._start_time = None
        self._elapsed_time = None

    def accept(self, visitor: Visitor[Node]) -> None:
        visitor.visit(self)

    @abc.abstractmethod
    async def start(self) -> None:
        """Start the execution of an idle test."""
        ...

    @abc.abstractmethod
    def suspend(self) -> None:
        """Suspend the execution of a running test."""
        ...

    @abc.abstractmethod
    def resume(self) -> None:
        """Resume the execution of a paused test."""
        ...

    @abc.abstractmethod
    def interrupt(self) -> None:
        """Interrupt the execution of a running test with a SIGINT signal."""
        ...

    @abc.abstractmethod
    def kill(self) -> None:
        """Interrupt the execution of a running test with a SIGKILL signal."""
        ...

    @abc.abstractmethod
    def terminate(self) -> None:
        """Interrupt the execution of a running test with a SIGTERM signal."""
        ...

    @property
    def name(self) -> str:
        """Name of a test."""
        return self._name

    @property
    def status(self) -> TestStatus:
        """Runtime status of a test."""
        return self._status

    @property
    def result(self):
        """Result of a finished test."""
        return self._result

    @property
    def command(self) -> TestCommand:
        """Test execution command representation as an object."""
        return self._command

    @property
    def end_time(self) -> time.time:
        """Time measured at the end of a test."""
        return self._end_time

    @property
    def start_time(self) -> time.time:
        """Time measured at the begining of a test."""
        return self._start_time

    @property
    def elapsed_time(self) -> time.time:
        """Time spent idle between start and stop measurements."""
        return self._elapsed_time


@dataclass(init=False)
class Test(TestBase, UIDMixin):
    """Holds information about a test."""

    flow: str
    seed: int

    def __init__(self, command: str | TestCommand, *args, **kwargs) -> None:
        if command is None:
            command = TestCommand("")
        elif isinstance(command, str):
            command = TestCommand(command)
        super().__init__(command, *args, **kwargs)
        try:
            self._name = command.test
        except AttributeError:
            raise
        if "/" in self._name:
            self._name = self._name.partition("/")[-1]
        self._flow = None
        self._seed = 0

    @property
    def flow(self):
        """The selected execution flow of the test."""
        try:
            rv = self.command.flow
        except AttributeError:
            raise
        else:
            return rv

    @property
    def seed(self):
        """Randomization seed of a test's RNG."""
        try:
            rv = int(self.command.seed)
        except AttributeError:
            rv = 0
        return rv

    @property
    def idle(self) -> bool:
        """True if test has no active process and has not yet started."""
        return self.process is None or self.process.status() == ps.STATUS_IDLE

    @property
    def running(self) -> bool:
        """True if test is currently running in a dedicated process."""
        return (
            self.process is not None
            and ps.pid_exists(self.process.pid)
            and self.process.is_running()
        )

    @property
    def finished(self) -> bool:
        """True if test finished running without normally interruption."""
        return (
            self.process is not None
            and ps.pid_exists(self.process.pid)
            and self.process.status() == ps.STATUS_ZOMBIE
        )

    @property
    def passed(self) -> bool:
        """True if test has finished running and no errors occured."""
        return self.result == TestResult.Passed

    @property
    def failed(self) -> bool:
        """True if test finished running and at least one error occured."""
        return self.result == TestResult.Failed

    @property
    def stdin(self) -> TextIO | None:
        """The standard input of the test's process or None if not running."""
        return self.process.stdin if self.process is not None else None

    @property
    def stdout(self) -> TextIO | None:
        """The standard output of the test's process or None if not running."""
        return self.process.stdout if self.process else None

    @property
    def stderr(self) -> TextIO | None:
        """The standard error of the test's process or None if not running."""
        return self.process.stderr if self.process else None

    @property
    def process(self) -> ps.Process:
        """The active process of the running test or None if not running."""
        return ps.Process(self._proc.pid)

    @property
    def returncode(self) -> int | None:
        """The return code from the test process or None if running or idle."""
        return self.process.returncode if self.finished else None

    @override
    async def start(self) -> None:
        """Start a test in a subprocess."""
        if not self.idle:
            msg = "Cannot start a test when it is already running."
            exc = OSError(msg)
            logger.exception(msg, exc_info=exc, stack_info=True)
            raise exc

        self._proc = await aio.create_subprocess_shell(
            cmd=self.command.line,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            loop=aio.get_event_loop(),
        )
        self._result = (
            TestResult.Passed
            if await self._proc.wait() == 0
            else TestResult.Failed
        )

    @override
    def suspend(self) -> None:
        """Send a keyboard interrupt (SIGINT) to stop a running test."""
        if self.running:
            self.process.suspend()

    @override
    def resume(self) -> None:
        """Resume the process if it is paused."""
        if self.running:
            self.process.resume()

    @override
    def wait(self, timeout: float | None = None) -> None:
        """Wait for a test to terminate if it is running."""
        if self.running:
            self.process.wait(timeout=timeout)

    @override
    def terminate(self) -> None:
        """Terminate the process with SIGTERM."""
        if self.running:
            self.process.terminate()

    @override
    def kill(self) -> None:
        """Kill the process with signal SIGKILL.

        Try using terminate prior to calling this method as kill does not allow
        the process to clean up properly on exit and terminate nicely.

        Kill should only ever be used when you NEED the process gone ASAP.
        """
        if self.running:
            self.process.kill()
