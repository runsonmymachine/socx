from __future__ import annotations

import time
import abc
import shlex
import asyncio as aio
import psutil as ps
from pathlib import Path
from subprocess import PIPE
from enum import auto
from enum import IntEnum
from typing import TextIO
from typing import override
from dataclasses import field
from dataclasses import dataclass

from .log import logger
from .config import settings
from .mixins import UIDMixin
from .visitor import Node
from .visitor import Visitor

# TODO: Patch - socrun should be modified to return non-zero value on
# test failure in the future
from socx_patches import post_process_sim_log as pp_simlog


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
        for i, attr in enumerate(self.args):
            if attr.startswith("--") or attr.startswith("-"):
                if attr == arg and i + 1 < len(self.args):
                    return self.args[i + 1]
                if attr.removeprefix("-") == arg and i + 1 < len(self.args):
                    return self.args[i + 1]
                if attr.removeprefix("--") == arg and i + 1 < len(self.args):
                    return self.args[i + 1]
        return None

    def __getattr__(self, attr: str) -> str:
        rv = self.extract_argv(attr)
        if rv is not None:
            return rv
        else:
            err = f"No such argument: {attr}"
            raise AttributeError(err)

    def __hash__(self) -> int:
        return hash(tuple(set(self.args)))


@dataclass(init=False)
class TestBase:
    """Definition of basic properties common accross all test types."""

    pid: int
    name: str
    command: TestCommand
    started_time: time.time
    finished_time: time.time

    def __init__(
        self, command: str | TestCommand | None = None, *args, **kwargs
    ) -> None:
        if command is None:
            command = ""
        if not isinstance(command, TestCommand):
            command = TestCommand(command)
        self._name = "BASE"
        self._proc = None
        self._status = TestStatus.Idle
        self._result = TestResult.NA
        self._command = command
        self._started_time = None
        self._finished_time = None

    def accept(self, visitor: Visitor[Node]) -> None:
        visitor.visit(self)

    @property
    def pid(self) -> int | None:
        """Name of a test."""
        return self._proc.pid if self._proc is not None else None

    @property
    def name(self) -> str:
        """Name of a test."""
        return self._name

    @property
    def command(self) -> TestCommand:
        """Test execution command representation as an object."""
        return self._command

    @property
    def status(self) -> TestStatus:
        """Status of a test."""
        return self._status

    @property
    def result(self):
        """Result of a finished test."""
        return self._result

    @property
    def started_time(self) -> time.time:
        """Time measured at the begining of a test."""
        return time.ctime(self._started_time)

    @property
    def finished_time(self) -> time.time:
        """Time measured at the end of a test."""
        return time.ctime(self._finished_time)

    @abc.abstractmethod
    async def start(self) -> None:
        """Start the execution of an idle test."""
        ...

    @abc.abstractmethod
    async def suspend(self) -> None:
        """Suspend the execution of a running test."""
        ...

    @abc.abstractmethod
    async def resume(self) -> None:
        """Resume the execution of a paused test."""
        ...

    @abc.abstractmethod
    async def interrupt(self) -> None:
        """Interrupt the execution of a running test with a SIGINT signal."""
        ...

    @abc.abstractmethod
    async def terminate(self) -> None:
        """Interrupt the execution of a running test with a SIGTERM signal."""
        ...

    @abc.abstractmethod
    async def kill(self) -> None:
        """Interrupt the execution of a running test with a SIGKILL signal."""
        ...


@dataclass(init=False)
class Test(TestBase, UIDMixin):
    """Holds information about a test."""

    flow: str
    seed: int
    build: int

    def __init__(self, command: str | TestCommand, *args, **kwargs) -> None:
        super().__init__(command, *args, **kwargs)
        try:
            name = self.command.test
        except AttributeError:
            self._missing_test_name_err(command)
        if "/" in name:
            name = name.partition("/")[-1]
        self._name = name
        self._seed = 0
        self._proc = None
        self._flow = None
        self._build = None

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
    def build(self):
        """Randomization build of a test's RNG."""
        try:
            return str(self.command.build)
        except AttributeError:
            return ""

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
        return self._proc is None

    @property
    def pending(self):
        """The test is scheduled to be started soon but has not yet started."""
        return self._status == TestStatus.Pending

    @property
    def started(self) -> bool:
        """True if test was started via a prior call to method `start`."""
        return self._proc is not None

    @property
    def suspended(self) -> bool:
        """True if test was started via a prior call to method `start`."""
        return self.started and self.process.status() == ps.STATUS_STOPPED

    @property
    def running(self) -> bool:
        """True if test is currently running in a dedicated process."""
        return self.started and self.returncode is None and not self.suspended

    @property
    def finished(self) -> bool:
        """True if test finished running without normally interruption."""
        return self.started and self.returncode is not None

    @property
    def terminated(self) -> bool:
        """True if test started but was intentionaly terminated."""
        return self.finished and self.returncode < 0

    @property
    def passed(self) -> bool:
        """True if test has finished running and no errors occured."""
        return self.finished and self.returncode == 0

    @property
    def failed(self) -> bool:
        """True if test finished running and at least one error occured."""
        return self.finished and self.returncode > 0

    @property
    def stdin(self) -> TextIO | None:
        """The standard input of the test's process or None if not running."""
        return self._proc.stdin.decode() if self.running else None

    @property
    def stdout(self) -> TextIO | None:
        """The standard output of the test's process or None if not running."""
        if self.finished:
            return self._stdout
        else:
            return None

    @property
    def stderr(self) -> TextIO | None:
        """The standard error of the test's process or None if not running."""
        if self.finished:
            return self._stderr
        else:
            return None

    @property
    def process(self) -> ps.Process:
        """The active process of the running test or None if not running."""
        if self._proc is None or not ps.pid_exists(self._proc.pid):
            return None
        else:
            return ps.Process(self._proc.pid)

    @property
    def returncode(self) -> int | None:
        """The return code from the test process or None if running or idle."""
        if self._proc is None or self._proc.returncode is None:
            return None
        return self._proc.returncode

    @property
    def rtp(self) -> Path:
        """
        Get the simulation's runtime path.

        The runtime referes to the path where compilation database and run logs
        are dumped by default by the simulator.
        """
        return settings.regression.runtime.path / self.dirname

    @property
    def dirname(self):
        """The simulation's runtime directory name."""
        return Path(self.command.test).with_suffix("")

    @override
    async def start(self) -> None:
        """Start a test in a subprocess."""
        if not self.idle:
            msg = "Cannot start a test when it is already running."
            exc = OSError(msg)
            logger.exception(msg, exc_info=exc, stack_info=True)
            raise exc

        def is_done():
            return self.returncode is not None

        cond = aio.Condition()
        self._status = TestStatus.Pending
        self._proc = await aio.create_subprocess_shell(
            cmd=self.command.line, stdin=None, stdout=PIPE, stderr=PIPE
        )
        try:
            stdout, stderr = await self._proc.communicate()
            self._status = TestStatus.Running
            self._started_time = time.time()
            await cond.wait_for(is_done)
            self._finished_time = time.time()
            self._stdout = stdout.decode()
            self._stderr = stderr.decode()
        except Exception:
            self.terminate()
            self._status = TestStatus.Terminated
            self._result = TestResult.Failed
            logger.exception(
                f"""Test failed: an exception was raised during execution \
                of '{self.name}'""".strip(),
                exc_info=True,
            )
        else:
            await self._proc.wait()
            self._status = TestStatus.Finished
            self._result = self._parse_result()

    @override
    def suspend(self) -> None:
        """Send a SIGSTOP signal to suspend the test's running process."""
        if self.running:
            self.process.suspend()

    @override
    def resume(self) -> None:
        """Resume the process if it is paused (sends a SIGCONT signal)."""
        if self.suspended:
            self.process.resume()

    @override
    def wait(self, timeout: float | None = None) -> None:
        """Wait for a test to terminate if it is running."""
        if self.running:
            self.process.wait()

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

    def _parse_result(self) -> TestResult:
        logger.debug(f"parsing result from {self.rtp}")
        result_hack = pp_simlog.TestResults()
        result_hack.reset_log(self.rtp)
        try:
            result_hack.parse_log()
        except ValueError:
            return TestResult.Failed
        else:
            return TestResult.from_temporary_hack(result_hack)

    def __hash__(self) -> int:
        return hash(self.command)

    @classmethod
    def _missing_test_name_err(cls, cmd) -> ValueError:
        err = f"No test was specified in the run command: {cmd}"
        exc = ValueError(err)
        logger.exception(err, exc_info=exc)
        raise exc


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

    def from_temporary_hack(self, hack: pp_simlog.TestResults) -> TestResult:
        match hack.result:
            case "NA":
                return TestResult.NA
            case "PASS":
                return TestResult.Passed
            case "FAIL":
                return TestResult.Failed


class TestStatus(IntEnum):
    """
    TestStatus representation of a test process as an `IntEnum`.

    Members
    -------
    Idle: IntEnum
        Idle, waiting to be scheduled for execution.

    Pending: IntEnum
        Test is scheduled for execution in an active session.

    Running: IntEnum
        Test is currently running.

    Stopped: IntEnum
        Test has been stopped intentionaly.

    Finished: IntEnum
        Test had finished running normally with an exit code 0.

    Terminated: IntEnum
        Test was intentionally terminated by a signal.
    """

    Idle = auto(0)
    Pending = auto()
    Running = auto()
    Stopped = auto()
    Finished = auto()
    Terminated = auto()
