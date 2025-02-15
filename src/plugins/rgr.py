import click

from socx import command, group, console, settings, Test

@group("rgr", plugin=False)
def cli():
    """Perform various regression related actions."""


@command(parent=cli)
def rerun_history():
    """Rerun all failed tests from the dawn of history of regressions."""
    failure_history = settings.regression.failure_history
    history_fp = failure_history.parent/failure_history.name
    with click.open_file(history_fp, mode="r", encoding="utf-8") as file:
        for line in file:
            console.print(Test(line))


@command(parent=cli)
def rrfh():
    """Alias for rerun-failed-history command."""
    rerun_history()
