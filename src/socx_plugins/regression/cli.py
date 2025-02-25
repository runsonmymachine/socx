import asyncio as aio
from socx import cli as soc_cli
from socx_plugins.regression.rgr import rerun_fail_hist


@soc_cli.group("rgr")
def cli():
    """Perform various regression related actions."""


@cli.command()
def rrfh():
    """Command alias of rerun-failure-history."""
    aio.run(rerun_fail_hist())


@cli.command()
def rerun_failure_history():
    """Rerun failed tests from all past regressions."""
    aio.run(rerun_fail_hist())
