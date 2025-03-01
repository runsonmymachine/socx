import rich_click as click
from rich.syntax import Syntax
from rich.prompt import Confirm

from socx import console
from socx import settings

@click.command("example")
def cli():
    """Command-line-interface plugin example."""
    style = "[magenta on gray23][bold][underline]"

    text = """
    :wave: Hello from plugin example! :wave:

    The code for this example can be found under plugins/example.py

    To highlight how simple it is to write a plugin, as complex as it may seem,
    the code for this example can even print itself as its own example!

    👇👇👇 See code below 👇👇👇
    """

    code = Syntax.from_path(
        tab_size=4,
        theme="nord",
        word_wrap=False,
        line_numbers=True,
        indent_guides=True,
        path=settings.plugins.example.path
    )

    console.clear()
    console.line(3)
    console.print(f"{style}{text}", justify="center")
    console.line(3)

    if Confirm.ask(
        console=console, prompt="Display the code for this example?"
    ):
        console.rule(f"{style}Plugin Code:")
        console.line(3)
        console.print(code)
    else:
        console.print("Goodbye :)")
