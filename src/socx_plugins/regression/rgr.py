import click

from pathlib import Path

from socx import Test
from socx import console
from socx import settings


def rerun_fail_hist():
    failure_history = settings.regression.files.failure_history
    history_fp = Path(failure_history.parent) / failure_history.name
    with click.open_file(history_fp, mode="r", encoding="utf-8") as file:
        for line in file:
            console.print(Test(line))
