from socx import LstConverter
from socx import cli as soc_cli

@soc_cli.group("convert")
def cli():
    """Perform a conversion based on current configurations."""

@cli.command()
def lst():
    """Convert symbol tables from an LST file to SystemVerilog covergroups."""
    LstConverter().convert()

