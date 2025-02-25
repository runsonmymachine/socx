from socx import cli as soc_cli
from socx_plugins.regression.rgr import rerun_fail_hist


@soc_cli.group("rgr")
def cli():
    """Perform various regression related actions."""


@cli.command()
def rrfh():
    """Command alias of rerun-failure-history."""
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(rerun_fail_hist())


@cli.command()
def rerun_failure_history():
    """Rerun failed tests from all past regressions."""
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(rerun_fail_hist())
