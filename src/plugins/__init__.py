"""
Plugins for socker.

The cli directory contains command-line-interface plugins loaded as subcommands
for `socker` cli.

The languages directory containts plugins for the language conversion tool
`socker convert <language>`, for example, to add support for json conversions.

simply add a file plugins/languages/json.py with a main `cli` function defined
as such:

>>> import click

    @click.pass_context
    def cli(ctx: click.Context) -> int:
        \"\"\"My json conversion plugin.\"\"\"
        file = ctx.inputfile
        # ...  do some stuff
        try:
            file.write(json_converter.exec())
        except ConversionError:
            return -1
        else:
            return 0;

    if __name__ == "__main__":
        cli({})
"""


__all__ = (
    "cli",
    "tui",
    "languages",
)


from . import cli as cli
from . import tui as tui
from . import languages as languages
