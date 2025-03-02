from enum import IntEnum
from enum import auto

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


