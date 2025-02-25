from __future__ import annotations

import time
import asyncio as aio
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
    pending: aio.Queue
    running: aio.Queue[Test]
    done: aio.Queue[Test]

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
        self._name: str = name
        self._lock: aio.Lock = aio.Lock()
        self._tests: dict[str, Test] = {test.name: test for test in tests}
        self._result: RegressionResult = RegressionResult.NA
        self._status: RegressionStatus = RegressionStatus.Idle
        self._progress: ProgressBar = ProgressBar(width=50, total=len(tests))
        self.pending: aio.Queue = aio.Queue(maxsize=len(tests))
        self.running: aio.Queue = aio.Queue(maxsize=self.run_limit)
        self.done: aio.Queue = aio.Queue(maxsize=len(tests))

    def accept(self, visitor: Visitor[Node]) -> None:
        """Accept a visit from a visitor."""
        visitor.visit(self)

    def __iter__(self) -> Iterator[Test]:
        """Iterate over tests defined in a regression."""
        return iter(self.tests.items())

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
        rv = int(self.cfg.max_runs_in_parallel)
        return rv

    @override
    async def start(self) -> None:
        """Start the execution of an idle test."""
        tasks = [
            aio.create_task(self.update_progress(), name="update_progress"),
            aio.create_task(self.schedule_tests(), name="schedule_tests"),
            aio.create_task(
                self.run_schedule(),
                name="start_tests",
            ),
            aio.create_task(self.collect_runs(), name="collect_results"),
        ]
        done = await aio.gather(*tasks)
        for result in done:
            logger.debug(result)

    async def schedule_tests(self) -> None:
        for test in list(self.tests.values()):
            await self.schedule_test(test)

    async def schedule_test(self, test) -> None:
        logger.debug(f"Scheduling {test.name} for execution...")
        try:
            await self.pending.put(test)
        except Exception as exc:
            err = f"A {type(exc)} exception was raised during scheduling."
            logger.exception(err, exc_info=exc)
            raise exc
        else:
            test._status = TestStatus.Pending
        logger.debug(f"Succesfuly scheduled test {test.name} for execution.")

    async def run_schedule(self) -> None:
        workers = []
        while self.pending.qsize() or self.running.qsize():
            n = self.run_limit - len(workers)
            if n > 0:
                logger.debug(f"creating {n} new runners...")
                workers = [
                    aio.create_task(self.run_next_in_sched(), name="runner")
                    for _ in range(n)
                ] + list(workers)
                logger.debug(f"created {n} new runners.")
            if workers:
                done, workers = await aio.wait(workers)
                logger.debug(f"{len(done)} runners were awaited.")
                logger.debug(f"{len(workers)} runners are still pending.")
        logger.debug("All scheduled tasks were started.")
        for worker in workers:
            if not worker.cancelled():
                logger.debug(f"canceling irrelevant {worker.get_name()}...")
                worker.cancel()
                logger.debug(f"{worker.get_name()} cancelled.")

    async def run_next_in_sched(self):
        exc = None
        test = await self.pending.get()
        try:
            task = aio.create_task(test.start(), name=test.name)
            logger.debug(f"Runner({task.get_name()}): running test...")
            await self.running.put(task)
            await task
        except Exception as e:
            exc = e
            err = f"Runner task was canceled due to {type(exc)} exception."
            logger.exception(err, exc_info=exc)
        finally:
            self.pending.task_done()
        if exc:
            raise exc

    async def collect_runs(self) -> None:
        total = len(self.tests.values())
        workers = []
        while self.done.qsize() < total:
            if self.running.empty():
                await aio.sleep(0)
                continue
            n = self.run_limit - len(workers)
            if n > 0:
                logger.debug(f"creating {n} new collectors...")
                workers = [
                    aio.create_task(self.collect_one(), name="collector")
                    for _ in range(n)
                ] + list(workers)
                logger.debug(f"created {n} new collectors.")
            if workers:
                done, workers = await aio.wait(workers)
                logger.debug(f"{len(done)} collectors were awaited.")
                logger.debug(f"{len(workers)} collectors are still pending.")
        logger.debug("All results were succesfuly collected.")
        for worker in workers:
            if not worker.cancelled():
                logger.debug(f"canceling irrelevant {worker.get_name()}...")
                worker.cancel()
                logger.debug(f"{worker.get_name()} cancelled.")

    async def collect_one(self) -> None:
        exc = None
        task = await self.running.get()
        try:
            logger.debug(f"Collector: collected task {task.get_name()}")
            if not task.done():
                logger.debug(
                    f"Collector: waiting for task '{task.get_name()}' to finish"
                )
                await task
            await self.done.put(task)
            logger.debug(f"Collector: task '{task.get_name()}' done.")
        except Exception as e:
            task.cancel()
            err = f"Collector cancelled due to {type(e)} exception."
            logger.exception(err, exc_info=e)
            raise
        finally:
            self.running.task_done()

    async def update_progress(self) -> None:
        current = 0
        total = len(self.tests.values())
        self.progress.update(current, total)
        while self.progress.completed < total:
            self.progress.update(self.done.qsize())
            await self.draw_progress()

    async def draw_progress(self) -> None:
        bar = self.progress
        progress = f"({self.done.qsize()}/{len(self)})"
        with console.capture() as cap:
            console.show_cursor(False)
            console.print(bar, end=" ")
            console.print(progress)
        console.file.write("\r" + cap.get().strip())
        await aio.sleep(0.2)
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
