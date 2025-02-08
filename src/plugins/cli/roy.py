import click

@click.command()
def cli():
    """Command example plugin invoked by calling `covgen roy`."""
    print("Hello from Roy")
