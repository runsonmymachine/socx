import click as click


@click.command()
def cli():
    """Command example plugin."""
    click.secho("Hello from test plugin!", color="purple", underline=True)
