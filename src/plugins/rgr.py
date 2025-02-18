import click

from socx import console, settings, Test, cli as soc_cli


@soc_cli.group("rgr")
def cli():
    """Perform various regression related actions."""


@cli.command()
def rrfh():
    """Command alias of rerun-failure-history."""
    failure_history = settings.regression.files.failure_history
    history_fp = failure_history.parent / failure_history.name
    with click.open_file(history_fp, mode="r", encoding="utf-8") as file:
        for line in file:
            console.print(Test(line))


@cli.command("rerun-failure-history")
def rerun_failure_history():
    """Rerun failed tests from all past regressions."""
    rrfh()


