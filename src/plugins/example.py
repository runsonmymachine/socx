from rich.syntax import Syntax
from rich.prompt import Confirm

from socx import console, command, settings

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
    word_wrap=False,
    line_numbers=True,
    indent_guides=True,
    theme="nord",
    path=settings.plugins.path / "example.py",
)


@command()
def cli():
    """Command-line-interface plugin example."""
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
