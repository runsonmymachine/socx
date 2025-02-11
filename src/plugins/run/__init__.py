import click

from socx import command, group, console

@group("run", plugin=True)
def cli():
    """Run a test, tool, GUI application, etc..."""


@command("help", parent=cli)
@click.argument("command", required=False, default=None, type=str)
@click.pass_context
def help_(ctx: click.Context, command: str):
    """Print usage and help information."""
    cmd = cli.get_command(ctx, command) if command else None
    help_text = cmd.get_help(ctx) if cmd else cli.get_help(ctx)
    rule_text = f"{ctx.command_path}{f'->{cmd.name}' if cmd else ''}"
    rule_style = "[magenta on gray30]"
    console.rule(f"{rule_style}{rule_text}", align="center")
    console.print(f"{help_text}")
    console.rule("")
