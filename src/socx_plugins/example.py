import rich
import rich_click as click
from socx import console, settings

HELP_TEXT = """
 [magenta underline]
:wave: Hello from plugin example! :wave:

The code for this example can be found under plugins/example.py

To highlight how simple it is to write a plugin, as complex as it may seem,
the code for this example can even print itself as its own example!

👇👇👇 See code below 👇👇👇
[/]
"""


@click.command("example")
def cli():
    """Command-line-interface plugin example."""
    code = rich.syntax.Syntax.from_path(
        theme="monokai",
        tab_size=4,
        word_wrap=False,
        line_numbers=True,
        path=settings.plugins.example.entry.__file__
    )

    console.line(2)
    console.print(f"{HELP_TEXT}", justify="center")
    console.line(2)

    if rich.prompt.Confirm.ask("Display the code of this example plugin?"):
        console.print(code)
    else:
        console.print("Goodbye :)")
