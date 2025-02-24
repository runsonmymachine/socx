import asyncio as aio
from pathlib import Path

import click

from socx import Regression
from socx import settings


def rerun_fail_hist():
    failure_history = settings.regression.logs.files.failure_history
    history_fp = Path(failure_history.directory) / failure_history.filename
    with click.open_file(history_fp, mode="r", encoding="utf-8") as file:
        regression = Regression.from_lines("rgr", tuple(line for line in file))
    aio.run(regression.start())
