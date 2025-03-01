import rich_click as click

from socx_plugins.regression._opts import input_opt
from socx_plugins.regression._opts import output_opt


@click.group("rgr")
def cli():
    """Perform various regression related actions."""


@cli.command()
@input_opt()
@output_opt()
def run(input, output):  # noqa: A002
    """Run a regression from a file of 'socrun' commands."""
    import asyncio
    from socx_plugins.regression._cli import _run_from_file

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_run_from_file(input, output))


@cli.command()
@input_opt()
@output_opt()
def rrfh(input, output):  # noqa: A002
    """Command alias for rerun-failure-history."""
    import asyncio
    from socx_plugins.regression._cli import _run_from_file

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_run_from_file(input, output))


@cli.command()
@input_opt()
@output_opt()
def rerun_failure_history(input, output):  # noqa: A002
    """Rerun failed tests from all past regressions."""
    import asyncio
    from socx_plugins.regression._cli import _run_from_file

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_run_from_file(input, output))

