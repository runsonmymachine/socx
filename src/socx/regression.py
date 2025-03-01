from __future__ import annotations

import asyncio as aio
from time import strftime
from enum import auto
from enum import IntEnum
from pathlib import Path
from typing import override
from dataclasses import dataclass
from collections import deque
from collections.abc import Iterator
from collections.abc import Iterable

from click import open_file
from rich.panel import Panel
from rich.progress import Progress
from rich.progress import TextColumn
from rich.progress import BarColumn
from rich.progress import TaskProgressColumn
from rich.progress import TimeRemainingColumn
from rich.progress import SpinnerColumn
from rich.progress import TimeElapsedColumn
from rich.progress import MofNCompleteColumn
from dynaconf.utils.boxing import DynaBox

from .console import console
from .config import USER_LOG_DIR
from .log import get_logger
from .test import Test
from .test import TestBase
from .test import TestStatus
from .test import TestResult
from .config import settings
from .visitor import Node
from .visitor import Visitor
from .config import USER_LOG_DIR


logger = get_logger(__name__, USER_LOG_DIR / f"{__name__}.log")


__all__ = ("Regression", "RegressionStatus", "RegressionResult")


class RegressionResult(IntEnum):
    """
    Represents the result of a regression that had finished and exited
    normally.

    Members
    -------
    NA: RegressionResult
        Regression has not yet finished running and therefore result is
        non-applicable.

    Passed: RegressionResult
        Regression had finished and terminated normally with no errors and a 0
        exit code.

    Failed: RegressionResult
        Regression had finished either normally or abnormally with a non-zero
        exit code.
    """

    NA = auto()
    Passed = auto()
    Failed = auto()


class RegressionStatus(IntEnum):
    """
    Regression process status enum representation.

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


@dataclass(init=False)
class Regression(TestBase):
    tests: dict[str, Test]
    lock: aio.Lock
    done: aio.Queue[Test]
    pending: aio.Queue

    @classmethod
    def from_lines(cls, name: str, lines: Iterable[str]) -> Regression:
        tests = deque(Test(line) for line in lines)
        return Regression(name, tests)

    def __init__(self, name: str, tests: Iterable[Test], *args, **kwargs):
        TestBase.__init__(self, name, *args, **kwargs)
        if tests is None:
            tests = []
        elif not isinstance(tests, list):
            tests = list(tests)
        self.lock = aio.Lock()
        self.pending: aio.Queue = aio.Queue(maxsize=len(tests))
        self.messages: aio.Queue[str] = aio.Queue()
        self.done: aio.Queue = aio.Queue(maxsize=len(tests))
        self._tests: dict[str, Test] = {test.name: test for test in tests}
        self._progress: Progress = Progress(
            SpinnerColumn(),
            MofNCompleteColumn(),
            *Progress.get_default_columns(),
            "Elapsed:\n",
            TimeElapsedColumn(),
            transient=False,
            expand=False,
        )
        self._total_tid = None
        self._scheduling_tid = None
        self._running_tid = None

    def accept(self, visitor: Visitor[Node]) -> None:
        """Accept a visit from a visitor."""
        visitor.visit(self)

    def __iter__(self) -> Iterator[Test]:
        """Iterate over tests defined in a regression."""
        return iter(self.tests.values())

    async def __aiter__(self) -> Iterator[Test]:
        """Iterate over tests defined in a regression."""
        for test in tuple(self.tests.values()):
            yield test

    def __len__(self) -> int:
        return len(self.tests.values())

    def __contains__(self, test: Test) -> bool:
        return test is not None and test in self.tests

    def __getitem__(self, index: str) -> Test | Iterable[Test]:
        return self.tests.__getitem__(index)

    @property
    def cfg(self) -> DynaBox:
        return settings.regression

    @property
    def tests(self) -> dict[str, Test]:
        """An iterable of all tests defined in the regression."""
        return self._tests

    @property
    def run_limit(self):
        """The run_limit property."""
        return int(self.cfg.max_runs_in_parallel)

    @override
    async def start(self) -> None:
        """Start the execution of an idle test."""
        now = strftime("%H-%M")
        today = strftime("%d-%m-%Y")
        passed_file = open_file(
            str(Path(self.cfg.report.path) / today / f"{now}_passed.log"),
            mode="w",
            encoding="utf-8",
            lazy=True,
        )
        failed_file = open_file(
            str(Path(self.cfg.report.path) / today / f"{now}_failed.log"),
            mode="w",
            encoding="utf-8",
            lazy=True,
        )
        self._status = TestStatus.Pending
        try:
            async with aio.TaskGroup() as tg:
                tg.create_task(self._animate_progress())
                tg.create_task(self.schedule_tests())
                tg.create_task(self.run_tests())
                self._status = TestStatus.Running
        except Exception:
            self._status = TestStatus.Terminated
            self._result = TestResult.Failed
        else:
            self._status = TestStatus.Finished
            self._result = (
                TestResult.Passed
                if all(test.result == TestResult.Passed for test in self)
                else TestResult.Failed
            )
        finally:
            tests = set(iter(self))
            passed = {test for test in tests if test.passed}
            failed = tests.difference(passed)
            passed_file.write("\n".join(test.command.line for test in passed))
            failed_file.write("\n".join(test.command.line for test in failed))

    async def schedule_tests(self) -> None:
        self._progress.start_task(self._scheduling_tid)
        await self.messages.put("Scheduling tests...")
        async with aio.TaskGroup() as tg:
            async for test in self:  # removed async cause it was 2 fast
                tg.create_task(self.scheduler(test))
        await self.messages.put("All tests scheduled.")
        self._progress.stop_task(self._scheduling_tid)

    async def scheduler(self, test) -> None:
        self._progress.start_task(self._running_tid)
        await self.messages.put(f"Scheduler({test.name}): scheduling test...")
        try:
            test._status = TestStatus.Pending
            await self.pending.put(test)
        except Exception:
            logger.exception(
                f"Scheduler({test.name}): An exception occured while "
                "scheduling."
            )
        else:
            await self.messages.put(f"Scheduler({test.name}): test scheduled.")
            self._scheduler_done()
        finally:
            await self.pending.join()

    async def run_tests(self) -> None:
        ready = not self.pending.empty()
        while not ready:
            await aio.sleep(0)
            ready = not self.pending.empty()
        await self.messages.put("starting runners...")
        self._progress.start_task(self._running_tid)
        async with aio.TaskGroup() as tg:
            for _ in range(self.run_limit):
                tg.create_task(self.runner())
        await self.messages.put("all runners completed.")
        self._progress.stop_task(self._running_tid)

    async def runner(self):
        while self.pending.qsize():
            test = await self.pending.get()
            name = test.name
            task = aio.create_task(test.start())
            try:
                await self.messages.put(f"Runner({test.name}): test starting.")
                await task
            except Exception:
                logger.exception(
                    f"Runner({test.name}): test terminated due to exception."
                )
            else:
                await self.messages.put(
                    f"Runner({test.name}): test completed."
                )
            finally:
                self.pending.task_done()
                self._runner_done(name)

    @override
    def suspend(self) -> None:
        """Suspend the execution of a running test."""
        for test in self.tests.values():
            test.suspend()

    @override
    async def resume(self) -> None:
        """Resume the execution of a paused test."""
        for test in self.tests.values():
            test.resume()

    @override
    async def interrupt(self) -> None:
        """Interrupt the execution of a running test with a SIGINT signal."""
        for test in self.tests.values():
            test.interrupt()

    @override
    async def terminate(self) -> None:
        """Interrupt the execution of a running test with a SIGTERM signal."""
        for test in self.tests.values():
            test.terminate()

    @override
    async def kill(self) -> None:
        """Interrupt the execution of a running test with a SIGKILL signal."""
        for test in self.tests.values():
            test.kill()

    async def _animate_progress(self):
        try:
            with self._progress:
                self._scheduling_tid = self._progress.add_task(
                    "[yellow]Scheduler: Running...", total=len(self), start=False
                )
                self._running_tid = self._progress.add_task(
                    "[yellow]Runners: Running...", total=len(self), start=False
                )
                self._total_tid = self._progress.add_task(
                    "[yellow]Regression: Running...", total=None
                )
                while not self._progress.tasks[self._running_tid].finished:
                    msgs = []
                    while not self.messages.empty():
                        try:
                            msg = await self.messages.get()
                            msgs.append(msg)
                        finally:
                            self.messages.task_done()
                    if msgs:
                        self._progress.log("\n".join(msgs))
                    await aio.sleep(0)
        except Exception:
            logger.exception(console.export_text())

    def _scheduler_done(self, *args, **kwargs) -> None:
        task = self._progress.tasks[self._scheduling_tid]
        if task.completed + 1 >= task.total:
            self._progress.update(self._scheduling_tid, description="[light_green]Scheduling: Done.", advance=1)
        else:
            self._progress.update(self._scheduling_tid, advance=1)
        self._progress.update(self._total_tid, advance=1)

    def _runner_done(self, name: str) -> None:
        running = self._progress.tasks[self._running_tid]
        total = self._progress.tasks[self._total_tid]
        if running.completed + 1 >= running.total:
            self._progress.update(
                self._running_tid,
                advance=1,
                description="[light_green]Running: Done.",
            )
            self._progress.update(
                self._total_tid,
                description="[light_green]Regression: Done.",
                total=total.completed + 1,
            )
        else:
            self._progress.update(self._running_tid, advance=1)
        self._progress.update(self._total_tid, advance=1)
