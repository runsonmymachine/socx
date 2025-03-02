from __future__ import annotations

import asyncio as aio
from time import strftime
from pathlib import Path
from typing import override
from threading import RLock
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

from .test import Test
from .test import TestBase
from .test import TestStatus
from .test import TestResult
from ..log import get_logger
from ..config import settings
from ..config import USER_LOG_DIR
from ..console import console
from ..visitor import Node
from ..visitor import Visitor


logger = get_logger(__name__, USER_LOG_DIR / f"{__name__}.log")


__all__ = ("Regression", "RegressionStatus", "RegressionResult")


@dataclass(init=False)
class Regression(TestBase):
    tests: dict[str, Test]

    def __init__(self, name: str, tests: Iterable[Test], *args, **kwargs):
        TestBase.__init__(self, name, *args, **kwargs)
        if tests is None:
            tests = []
        seen = set()
        duplicates = [x for x in tests if x in seen and seen.add(x) is None]
        seen.clear()
        unique = [x for x in tests if x not in seen and seen.add(x) is None]
        if len(unique) != len(tests):
            error = f"""
            Note that as a set, the total number of tests in the regression
            has less tests than what the original input list of tests included.
            (i.e. some hashes of the tests were found to be duplicates).

            The original number of tests was: {len(tests)}.

            The total number of unique tests is: {len(unique)}.

            The suspected duplicate values are: {duplicates}.
            """
            logger.exception(error)
            raise ValueError(error)
        self.lock = RLock()
        self._runner_tid = None
        self._scheduler_tid = None
        self._regression_tid = None
        self._tests: list[Test] = unique
        self._num_tests = len(self._tests)
        self._progress: Progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            TaskProgressColumn(),
            BarColumn(),
            SpinnerColumn(),
            "[green]Completed:",
            MofNCompleteColumn(),
            "[yellow]Elapsed:",
            TimeElapsedColumn(),
            "[cyan]Remaining:",
            TimeRemainingColumn(),
            transient=False,
            expand=False,
        )
        self.pending: aio.Queue = aio.Queue(self.run_limit)
        self.messages: aio.Queue[str] = aio.Queue()

    @classmethod
    def from_lines(cls, name: str, lines: Iterable[str]) -> Regression:
        tests = deque(Test(line) for line in lines)
        return Regression(name, tests)

    def accept(self, visitor: Visitor[Node]) -> None:
        """Accept a visit from a visitor."""
        visitor.visit(self)

    def __len__(self) -> int:
        return self._num_tests

    def __iter__(self) -> Iterator[Test]:
        """Iterate over tests defined in a regression."""
        return iter(self._tests)

    def __contains__(self, test: Test) -> bool:
        return test is not None and test in self._tests

    @property
    def cfg(self) -> DynaBox:
        """Regression settings accessed via property."""
        with self.lock:
            return settings.regression

    @property
    def tests(self) -> dict[str, Test]:
        """An iterable of all tests defined in the regression."""
        with self.lock:
            return self._tests

    @property
    def progress(self):
        """The regression's progress."""
        with self.lock:
            return self._progress

    @property
    def run_limit(self):
        """The max_runs_in_parallel configuration accessed via property."""
        with self.lock:
            return int(self.cfg.max_runs_in_parallel)

    @override
    async def start(self) -> None:
        """Start the regression."""
        self._status = TestStatus.Pending
        now = strftime("%H-%M")
        today = strftime("%d-%m-%Y")
        tests = set(iter(self))
        report_dir = Path(self.cfg.report.path) / today
        report_dir.mkdir(parents=True, exist_ok=True)
        passed_filepath = report_dir / f"{now}_passed.log"
        failed_filepath = report_dir / f"{now}_failed.log"
        passed_file = open_file(
            str(passed_filepath), mode="w", encoding="utf-8", lazy=True
        )
        failed_file = open_file(
            str(failed_filepath), mode="w", encoding="utf-8", lazy=True
        )
        try:
            async with aio.TaskGroup() as tg:
                tg.create_task(self._animate_progress())
                tg.create_task(self._schedule_tests())
                tg.create_task(self._run_tests())
                self._status = TestStatus.Running
            self._status = TestStatus.Finished
            self._result = (
                TestResult.Passed
                if all(test.result == TestResult.Passed for test in self)
                else TestResult.Failed
            )
        except Exception:
            self._status = TestStatus.Terminated
            self._result = TestResult.Failed
            raise
        finally:
            passed = {test for test in tests if test.passed}
            failed = tests.difference(passed)
            passed_file.write("\n".join(test.command.line for test in passed))
            failed_file.write("\n".join(test.command.line for test in failed))

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

    async def _schedule_tests(self) -> None:
        try:
            await self.messages.put("Scheduling tests...")
            async with aio.TaskGroup() as tg:
                for test in self.tests:  # removed async cause it was 2 fast
                    tg.create_task(self._scheduler(test))
            await self.messages.put("All tests scheduled.")
        except Exception:
            raise

    async def _scheduler(self, test) -> None:
        try:
            test._status = TestStatus.Pending
            await self.messages.put(
                f"Scheduler({test.name}): scheduling test..."
            )
            await self.pending.put(test)
            await self.messages.put(f"Scheduler({test.name}): test scheduled.")
            self._scheduler_advance()
        except Exception:
            logger.exception("An exception occured during scheduling.")
            raise

    async def _run_tests(self) -> None:
        try:
            while self.pending.empty():
                await aio.sleep(0.1)
            await self.messages.put("starting runners...")
            async with aio.TaskGroup() as tg:
                for _ in range(self.run_limit):
                    tg.create_task(self._runner())
                self._runner_advance()
            await self.pending.join()
            await self.messages.put("all tests completed. stopping runners.")
        except Exception:
            logger.exception("Failed to start runners due to exception")
            raise

    async def _runner(self):
        try:
            while self.pending.qsize():
                try:
                    test = await self.pending.get()
                    await self.messages.put(f"Runner({test.name}): running...")
                    await aio.create_task(test.start())
                    await self.messages.put(f"Runner({test.name}): done.")
                    self._runner_advance()
                finally:
                    self.pending.task_done()
        except Exception:
            logger.exception(
                f"Runner({test.name}): terminated due to exception."
            )
            raise

    async def _animate_progress(self):
        try:
            with self.progress as progress:
                self._scheduler_start()
                self._runner_start()
                self._regression_start()
                while not progress.finished:
                    msgs = await self._process_messages()
                    if msgs:
                        progress.log(msgs)
                    await aio.sleep(0.02)
        except Exception:
            logger.exception("Regression halted due to exception")
            raise

    async def _process_messages(self) -> str:
        msgs = ""
        while not self.messages.empty():
            try:
                msgs += await self.messages.get()
            finally:
                self.messages.task_done()
        return msgs

    def _scheduler_start(self) -> None:
        if self._scheduler_tid is None:
            self._scheduler_tid = self.progress.add_task(
                description="[red]Schedulers: pending...",
                total=len(self),
                start=False,
                visible=True,
            )

    def _scheduler_advance(self) -> None:
        if self._scheduler_tid is not None:
            if not self.progress.tasks[self._scheduler_tid].started:
                self.progress.start_task(self._scheduler_tid)
                self.progress.update(
                    self._scheduler_tid,
                    description="[yellow]Schedulers: working...",
                    total=len(self),
                    refresh=True,
                )
                self._regression_advance()
            if not self.progress.tasks[self._scheduler_tid].finished:
                self.progress.update(
                    self._scheduler_tid, advance=1, refresh=True
                )
            if self.progress.tasks[self._scheduler_tid].finished:
                self._scheduler_finish()

    def _scheduler_finish(self) -> None:
        if self._scheduler_tid is not None:
            self.progress.update(
                task_id=self._scheduler_tid,
                description="[light_green]Schedulers: done.",
                refresh=True,
            )

    def _runner_start(self) -> None:
        if self._runner_tid is None:
            self._runner_tid = self.progress.add_task(
                description="[red]Runners: pending...",
                total=len(self),
                start=False,
                visible=True,
            )

    def _runner_advance(self) -> None:
        if self._runner_tid is not None:
            if not self.progress.tasks[self._runner_tid].started:
                self.progress.start_task(self._runner_tid)
                self.progress.update(
                    self._runner_tid,
                    description="[yellow]Runners: working...",
                    visible=True,
                    refresh=True,
                )
            else:
                self.progress.update(self._runner_tid, advance=1, refresh=True)
            if self.progress.tasks[self._runner_tid].finished:
                self._runner_finish()
                self._regression_finish()

    def _runner_finish(self) -> None:
        if self._runner_tid is not None:
            self.progress.update(
                task_id=self._runner_tid,
                description="[light_green]Runners: done.",
                refresh=True,
            )

    def _regression_start(self) -> None:
        if self._regression_tid is None:
            self._regression_tid = self.progress.add_task(
                description="[red]Regression: pending...",
                total=None,
                start=False,
                visible=True,
            )

    def _regression_advance(self) -> None:
        if self._regression_tid is not None:
            if self.progress.tasks[self._regression_tid].started:
                return
            self.progress.start_task(self._regression_tid)
            self.progress.update(
                self._regression_tid,
                description="[yellow]Regression: in progress...",
                visible=True,
                refresh=True,
            )

    def _regression_finish(self) -> None:
        if self._regression_tid is not None:
            self.progress.update(
                task_id=self._regression_tid,
                description="[light_green]Regression: done.",
                total=len(self) * 2,
                completed=len(self) * 2,
                visible=True,
                refresh=True,
            )
