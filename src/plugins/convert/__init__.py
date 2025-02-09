import click
from covgen.cli import CLIPlugin

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

@click.group("convert", cls=CLIPlugin, no_args_is_help=True)
def cli():
    """Perform a conversion based on current configurations."""



