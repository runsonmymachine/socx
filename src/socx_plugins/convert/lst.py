import rich_click as click

from socx import LstConverter


@click.group("lst")
def cli():
    """Perform a conversion based on current configurations."""


@cli.command()
def lst():
    """Convert symbol tables from an LST file to SystemVerilog covergroups."""
    LstConverter().convert()

