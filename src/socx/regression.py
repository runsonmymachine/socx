from __future__ import annotations

import time
import asyncio as aio
from enum import auto
from enum import IntEnum
from typing import override
from dataclasses import dataclass
from collections import deque
from collections.abc import Iterator
from collections.abc import Iterable

from rich.progress_bar import ProgressBar

from .log import logger
from .test import Test
from .test import TestBase
from .config import settings
from .console import console
from .visitor import Node
from .visitor import Visitor


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
    lock: aio.Lock
    tests: list[Test]
    pending: aio.Queue
    running: aio.Queue[Test]
    done: aio.Queue[Test]

    @classmethod
    def from_lines(cls, name: str, lines: Iterable[str]) -> Regression:
        tests = deque(Test(line) for line in lines)
        return Regression(name, tests)

    def __init__(self, name: str, tests: Iterable[Test], *args, **kwargs):
        if tests is None:
            tests = []
        TestBase.__init__(self, name, *args, **kwargs)
        self._name: str = name
        self._lock: aio.Lock = aio.Lock()
        self._tests: list[Test] = list(tests)
        self._result: RegressionResult = RegressionResult.NA
        self._status: RegressionStatus = RegressionStatus.Idle
        self._progress: ProgressBar = ProgressBar(width=50, total=len(tests))
        self.pending: aio.Queue = aio.Queue(len(tests))
        self.running: aio.Queue = aio.Queue(self.run_limit)
        self.done: aio.Queue = aio.Queue(len(tests))

    def accept(self, visitor: Visitor[Node]) -> None:
        """Accept a visit from a visitor."""
        visitor.visit(self)

    def __iter__(self) -> Iterator[Test]:
        """Iterate over tests defined in a regression."""
        return iter(self.tests())

    def __len__(self) -> int:
        return len(self.tests())

    def __contains__(self, test: Test) -> bool:
        return test is not None and test in self.tests()

    def __getitem__(self, index: int | slice) -> Test | Iterable[Test]:
        return self.tests().__getitem__(index)

    async def __aiter__(self) -> Iterator[Test]:
        """Iterate over tests defined in a regression."""
        return await aiter(self.tests())

    @property
    def lock(self) -> aio.Lock:
        """An asyncronous lock object."""
        return self._lock

    @property
    def tests(self) -> Iterable[Test]:
        """An iterable of all tests defined in the regression."""
        return self._tests

    @property
    async def tests_async(self) -> Iterable[Test]:
        """An iterable of all tests defined in the regression."""
        for test in self.tests:
            yield test

    @property
    def progress(self) -> ProgressBar:
        """A progress bar to represent the regression's current progress."""
        return self._progress

    @property
    def run_limit(self):
        """The run_limit property."""
        try:
            rv = int(settings.regression.max_runs_in_parallel)
        except AttributeError:
            rv = 10
        return rv

    @override
    async def start(self) -> None:
        """Start the execution of an idle test."""
        tasks = [
            aio.create_task(self.schedule_tests(self._tests)),
            aio.create_task(self.on_test_scheduled()),
            aio.create_task(self.collect_results()),
            aio.create_task(self.update_progress()),
        ]
        try:
            done, pending = await aio.wait(tasks)
        except Exception as exc:
            for task in tasks:
                task.cancel(f"Cancelled due to exception: {exc}")
            err = f"Encountered {type(exc)} exception during 'start' method"
            logger.exception(err, exc_info=exc)
            raise exc
        for task in pending:
            task.cancel()
        for result in done:
            logger.debug(result)
            console.print(result)

    async def schedule_tests(self, tests: set[Test]) -> None:
        for test in tests:
            try:
                logger.debug(f"Scheduling {test.name} for execution...")
                await self.schedule_test(test)
            except Exception as exc:
                err = (
                    f"Failed to schedule test {test.name} due to "
                    f"{type(exc)} exception."
                )
                logger.exception(err, exc_info=exc)
                raise exc
            else:
                logger.debug(
                    f"Succesfuly scheduled test {test.name} for execution."
                )

    async def schedule_test(self, test) -> None:
        task = aio.create_task(test.start(), name=test.name)
        try:
            await self.pending.put(task)
        except Exception as e:
            err = f"A {type(e)} exception was raised during scheduling."
            task.cancel(err)
            logger.exception(err, exc_info=e)
            raise

    async def on_test_scheduled(self) -> None:
        workers = []
        while not self.done.full():
            if self.running.full():
                await aio.sleep(0)
                continue
            n = self.pending.qsize() - len(workers)
            if n > 0:
                logger.debug(f"creating {n} new runners...")
                workers = [
                    aio.create_task(self.run_next_in_sched(), name="runner")
                    for _ in range(n)
                ] + list(workers)
                logger.debug(f"created {n} new runners.")
            elif n < 0:
                logger.debug(f"canceling {abs(n)} runners...")
                for _ in range(n):
                    workers.pop().cancel()
                logger.debug(f"canceled {abs(n)} runners.")
            if not workers:
                await aio.sleep(0)
                continue
            done, workers = await aio.wait(
                workers, timeout=5, return_when=aio.ALL_COMPLETED
            )
            logger.debug(f"{len(done)} runners were awaited.")
            logger.debug(f"{len(workers)} runners are still pending.")
        while workers:
            worker = workers.pop()
            if not worker.cancelled():
                worker.cancel()

    async def run_next_in_sched(self):
        exc = None
        task = await self.pending.get()
        try:
            await self.running.put(task)
        except Exception as e:
            task.cancel()
            exc = e
            err = f"Runner task was canceled due to {type(exc)} exception."
            logger.exception(err, exc_info=exc)
        finally:
            self.pending.task_done()
            if exc:
                raise exc

    async def collect_results(self) -> None:
        workers = []
        while not self.done.full():
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
            elif n < 0:
                logger.debug(f"canceling {abs(n)} collectors...")
                for _ in range(n):
                    worker: aio.Future = workers.pop()
                    worker.cancel()
                logger.debug(f"canceled {abs(n)} collectors.")
            if not workers:
                await aio.sleep(0)
                continue
            done, workers = await aio.wait(
                workers, timeout=5, return_when=aio.ALL_COMPLETED
            )
            logger.debug(f"{len(done)} collectors were awaited.")
            logger.debug(f"{len(workers)} collectors are still pending.")
        while workers:
            logger.debug("All results were succesfuly collected.")
            logger.debug("canceling exranous leftover collectors...")
            worker = workers.pop()
            if not worker.cancelled():
                logger.debug(f"canceling collector {worker.name}...")
                worker.cancel()
                logger.debug(f"cancel worker {worker.name} done.")

    async def collect_one(self) -> None:
        exc = None
        task = await self.running.get()
        try:
            if not task.done():
                await task
            await self.done.put(task)
        except Exception as e:
            task.cancel()
            exc = e
            err = f"Collector task cancelled due to {type(exc)} exception."
            logger.exception(err, exc_info=exc)
        finally:
            self.running.task_done()
            if exc:
                raise exc

    async def update_progress(self) -> None:
        total = len(self.tests)
        current = 0
        self.progress.update(current, total)
        while current < total:
            current = self.done.qsize()
            self.progress.update(current)
            try:
                coro = aio.create_task(self.draw_progress())
            except Exception as e:
                err = (
                    f"Encountered {type(e)} exception during progress update."
                )
                logger.exception(err, exc_info=e)
                coro.cancel()
                raise e
            else:
                await coro

    async def draw_progress(self) -> None:
        await aio.sleep(0.25)
        console.show_cursor(False)
        with console.capture() as cap:
            total = self.progress.total
            completed = self.progress.completed
            console.print("", end="\r")
            console.print(self.progress, end=" ")
            console.print(f"([blue]{completed}[/]/[green]{total}[/])")
        console.file.write(cap.get().strip() + "\r")
        await aio.sleep(0.25)
        console.show_cursor(True)

    @override
    def suspend(self) -> None:
        """Suspend the execution of a running test."""
        for test in self.tests:
            test.suspend()

    @override
    async def resume(self) -> None:
        """Resume the execution of a paused test."""
        for test in self.tests:
            test.resume()

    @override
    async def interrupt(self) -> None:
        """Interrupt the execution of a running test with a SIGINT signal."""
        for test in self.tests:
            test.interrupt()

    @override
    async def terminate(self) -> None:
        """Interrupt the execution of a running test with a SIGTERM signal."""
        for test in self.tests:
            test.terminate()

    @override
    async def kill(self) -> None:
        """Interrupt the execution of a running test with a SIGKILL signal."""
        for test in self.tests:
            test.kill()
