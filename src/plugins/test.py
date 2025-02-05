import click as click


@click.command()
def cli():
    click.secho("Hello from test plugin!", color="purple", underline=True)
