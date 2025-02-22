import itertools as it
from pathlib import Path

import click

from socx import Test
from socx import console
from socx import settings


def rerun_fail_hist():
    failure_history = settings.regression.logs.files.failure_history
    history_fp = Path(failure_history.directory) / failure_history.filename
    with click.open_file(history_fp, mode="r", encoding="utf-8") as file:
        for line in file:
            console.print(Test(line))
