from socx import cli as soc_cli

from socx_plugins.regression.rgr import rerun_fail_hist


@soc_cli.group("rgr")
def cli():
    """Perform various regression related actions."""
    pass

@cli.command()
def rrfh():
    """Command alias of rerun-failure-history."""
    rerun_fail_hist()

@cli.command()
def rerun_failure_history():
    """Rerun failed tests from all past regressions."""
    rerun_fail_hist()


