from __future__ import annotations

import time
import asyncio as aio
import contextlib
from functools import partial
from enum import auto
from enum import IntEnum
from typing import override
from dataclasses import dataclass
from collections import deque
from collections.abc import Iterator
from collections.abc import Iterable

from rich.progress_bar import ProgressBar
from dynaconf.utils.boxing import DynaBox

from .log import get_logger
from .test import Test
from .test import TestBase
from .test import TestStatus
from .test import TestResult
from .config import settings
from .console import console
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
        self.done: aio.Queue = aio.Queue(maxsize=len(tests))
        self.pending: aio.Queue = aio.Queue(maxsize=len(tests))
        self._tests: dict[str, Test] = {test.name: test for test in tests}
        self._progress: ProgressBar = ProgressBar(width=50, total=len(tests))

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
    def progress(self) -> ProgressBar:
        """A progress bar to represent the regression's current progress."""
        return self._progress

    @property
    def run_limit(self):
        """The run_limit property."""
        return int(self.cfg.max_runs_in_parallel)

    @override
    async def start(self) -> None:
        """Start the execution of an idle test."""
        self._status = TestStatus.Pending
        tasks = {
            aio.create_task(self.schedule_tests(), name="schedule_tests"),
            aio.create_task(self.run_schedule(), name="start_tests"),
            aio.create_task(self.fetch_results(), name="fetch_results"),
        }
        self._status = TestStatus.Running
        results = await aio.gather(*tasks)
        for result in results:
            self.print(result)
        self._status = TestStatus.Finished
        self._result = (
            TestResult.Passed
            if all(test.result == TestResult.Passed for test in self)
            else TestResult.Failed
        )
        return results

    async def print(self, *args, **kwargs) -> None:
        async with self.lock:
            console.print(*args, **kwargs)

    async def log(self, *args, **kwargs) -> None:
        async with self.lock:
            logger.info(*args, **kwargs)

    async def schedule_tests(self) -> None:
        async for test in self:
            await self.schedule_test(test)
        await self.pending.join()

    async def schedule_test(self, test) -> None:
        await self.log(f"Scheduling {test.name} for execution...")
        test._status = TestStatus.Pending
        await self.pending.put(test)
        await self.log(f"Succesfuly scheduled test {test.name} for execution.")

    async def run_schedule(self) -> None:
        tasks = set()
        for _ in range(self.run_limit):
            task = aio.create_task(self.make_runner())
            tasks.add(task)
            task.add_done_callback(tasks.discard)
        await self.pending.join()
        await self.done.join()
        _, pending = await aio.wait(tasks, timeout=1)
        for runner in pending:
            if not runner.cancelled():
                runner.cancel()

    async def make_runner(self):
        while True:
            if self.pending.empty():
                await self.done.join()
                return
            try:
                test = await self.pending.get()
                await self.log(f"Runner({test.name}): running test...")
                await test.start()
                await self.done.put(test)
                await self.log(f"Runner({test.name}): test finished.")
            finally:
                self.pending.task_done()

    async def fetch_results(self) -> set:
        results = set()
        cnt, total, bar = 0, len(self), self.progress
        drawing = aio.create_task(self.draw_progress())
        while cnt < total:
            result = await self.done.get()
            async with self.lock:
                cnt += 1
                results.add(result)
                self.done.task_done()
                bar.update(cnt)
        await aio.wait({aio.ensure_future(drawing)}, timeout=3)
        if not drawing.cancelled():
            drawing.cancel()
        return results

    async def draw_progress(self) -> None:
        done = False
        while not done:
            await aio.sleep(0.1)
            async with self.lock:
                console.show_cursor(False)
                with console.capture() as cap:
                    bar = self.progress
                    done = bool(bar.completed >= bar.total)
                    progress = f"({bar.completed}/{bar.total})"
                    console.print(bar, end=" ")
                    console.print(progress)
                console.file.write("\r" + cap.get().strip())
                await aio.sleep(0.1)
                console.show_cursor(True)

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
