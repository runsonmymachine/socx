import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

@click.command(context_settings=CONTEXT_SETTINGS)
def cli():
    """Convert symbol tables from an LST file to SystemVerilog covergroups."""
