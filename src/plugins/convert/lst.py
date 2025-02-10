import click

from covgen import parse, command

@command()
@click.pass_context
def cli(ctx: click.Context):
    """Convert symbol tables from an LST file to SystemVerilog covergroups."""
    ctx.invoke(parse)
