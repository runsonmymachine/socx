from typing import Literal
import rich
import rich_click.rich_click as rich_cfg

from ..config import settings
from ..config import APP_NAME

__all__ = ("cli",)

from .cli import cli as cli

# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------

ColorSystem = Literal["auto", "standard", "256", "truecolor", "windows"]
MarkupOption = Literal["ansi", "rich", "markdown", None]

# -----------------------------------------------------------------------------
# Styles
# -----------------------------------------------------------------------------

rich_cfg.TEXT_MARKUP = "rich"
rich_cfg.STYLE_OPTION: rich.style.StyleType = "bright_green"
rich_cfg.STYLE_SWITCH: rich.style.StyleType = "bright_green"
rich_cfg.STYLE_COMMAND: rich.style.StyleType = "cyan"
rich_cfg.STYLE_ARGUMENT: rich.style.StyleType = "green"
rich_cfg.STYLE_ABORTED: rich.style.StyleType = "red"
rich_cfg.STYLE_DEPRECATED: rich.style.StyleType = "red"

rich_cfg.STYLE_HEADER_TEXT: rich.style.StyleType = ""
rich_cfg.STYLE_EPILOG_TEXT: rich.style.StyleType = ""
rich_cfg.STYLE_FOOTER_TEXT: rich.style.StyleType = ""

rich_cfg.STYLE_USAGE: rich.style.StyleType = "yellow"
rich_cfg.STYLE_USAGE_COMMAND: rich.style.StyleType = "cyan"

rich_cfg.STYLE_HELPTEXT: rich.style.StyleType = ""
rich_cfg.STYLE_HELPTEXT_FIRST_LINE: rich.style.StyleType = ""

rich_cfg.STYLE_REQUIRED_LONG: rich.style.StyleType = "red"
rich_cfg.STYLE_REQUIRED_SHORT: rich.style.StyleType = "red"

rich_cfg.STYLE_METAVAR: rich.style.StyleType = "yellow"
rich_cfg.STYLE_METAVAR_APPEND: rich.style.StyleType = "dim yellow"
rich_cfg.STYLE_METAVAR_SEPARATOR: rich.style.StyleType = "dim"

rich_cfg.STYLE_OPTION_HELP: rich.style.StyleType = ""
rich_cfg.STYLE_OPTION_ENVVAR: rich.style.StyleType = "dim yellow"
rich_cfg.STYLE_OPTION_DEFAULT: rich.style.StyleType = "magenta"

rich_cfg.ALIGN_OPTIONS_PANEL: rich.align.AlignMethod = "left"
rich_cfg.STYLE_OPTIONS_PANEL_BOX: str | rich.box.Box | None = "ROUNDED"
rich_cfg.STYLE_OPTIONS_PANEL_BORDER: rich.style.StyleType = "bright_black"

rich_cfg.STYLE_OPTIONS_TABLE_BOX: str | rich.box.Box | None = "HORIZONTAL"
rich_cfg.STYLE_OPTIONS_TABLE_LEADING: int = 0
rich_cfg.STYLE_OPTIONS_TABLE_PADDING: rich.padding.PaddingDimensions = (1, 1)
rich_cfg.STYLE_OPTIONS_TABLE_PAD_EDGE: bool = False
rich_cfg.STYLE_OPTIONS_TABLE_SHOW_LINES: bool = True
rich_cfg.STYLE_OPTIONS_TABLE_BORDER_STYLE: rich.style.StyleType | None = None
rich_cfg.STYLE_OPTIONS_TABLE_ROW_STYLES: list[rich.style.StyleType] | None = (
    None
)

rich_cfg.ALIGN_COMMANDS_PANEL: rich.align.AlignMethod = "left"
rich_cfg.STYLE_COMMANDS_PANEL_BOX: str | rich.box.Box | None = "ROUNDED"
rich_cfg.STYLE_COMMANDS_PANEL_BORDER: rich.style.StyleType = "bright_black"

rich_cfg.STYLE_COMMANDS_TABLE_BOX: str | rich.box.Box | None = ""
rich_cfg.STYLE_COMMANDS_TABLE_PADDING: rich.padding.PaddingDimensions = (0, 1)
rich_cfg.STYLE_COMMANDS_TABLE_LEADING: int = 1
rich_cfg.STYLE_COMMANDS_TABLE_PAD_EDGE: bool = True
rich_cfg.STYLE_COMMANDS_TABLE_SHOW_LINES: bool = False
rich_cfg.STYLE_COMMANDS_TABLE_BORDER_STYLE: rich.style.StyleType | None = None
rich_cfg.STYLE_COMMANDS_TABLE_ROW_STYLES: list[rich.style.StyleType] | None = (
    None
)
rich_cfg.STYLE_COMMANDS_TABLE_COLUMN_WIDTH_RATIO: tuple[int, int] = (
    None,
    None,
)

rich_cfg.ALIGN_ERRORS_PANEL: rich.align.AlignMethod = "left"
rich_cfg.STYLE_ERRORS_PANEL_BOX: str | rich.box.Box | None = "ROUNDED"
rich_cfg.STYLE_ERRORS_PANEL_BORDER: rich.style.StyleType = "red"
rich_cfg.STYLE_ERRORS_SUGGESTION: rich.style.StyleType = ""
rich_cfg.STYLE_ERRORS_SUGGESTION_COMMAND: rich.style.StyleType = "blue"

# -----------------------------------------------------------------------------
# Options
# -----------------------------------------------------------------------------

rich_cfg.COLOR_SYSTEM: ColorSystem = "auto"
"""Set to None to disable colors"""

rich_cfg.USE_MARKDOWN: bool = True
"""Parse help strings as markdown"""

rich_cfg.SHOW_ARGUMENTS: bool = True
"""Show positional arguments"""

rich_cfg.USE_RICH_MARKUP: bool = True
"""Parse help strings for rich markup (eg. [red]my text[/])"""

rich_cfg.USE_MARKDOWN_EMOJI: bool = True
"""Parse emoji codes in markdown :smile:"""

rich_cfg.OPTION_ENVVAR_FIRST: bool = False
"""Show env vars before option help text instead of avert"""

rich_cfg.APPEND_METAVARS_HELP: bool = False
"""Append metavar (eg. [TEXT]) after the help text"""

rich_cfg.USE_CLICK_SHORT_HELP: bool = False
"""Use click's default function to truncate help text"""

rich_cfg.SHOW_METAVARS_COLUMN: bool = False
"""Show a column with the option metavar (eg. INTEGER)"""

rich_cfg.GROUP_ARGUMENTS_OPTIONS: bool = False
"""Show arguments with options instead of in own panel"""

# -----------------------------------------------------------------------------
# Texts
# -----------------------------------------------------------------------------

rich_cfg.HEADER_TEXT: str = ""
rich_cfg.EPILOG_TEXT: str = ""
rich_cfg.FOOTER_TEXT: str = ""
rich_cfg.ABORTED_TEXT: str = "Aborted"

rich_cfg.ERRORS_PANEL_TITLE: str = "Error"
rich_cfg.OPTIONS_PANEL_TITLE: str = "Options"
rich_cfg.COMMANDS_PANEL_TITLE: str = "Commands"
rich_cfg.ARGUMENTS_PANEL_TITLE: str = "Arguments"

rich_cfg.RANGE_STRING: str = " [{}]"
rich_cfg.ENVVAR_STRING: str = "[envvar: {}]"
rich_cfg.DEFAULT_STRING: str = "(default={})"
rich_cfg.DEPRECATED_STRING: str = "(Deprecated) "
rich_cfg.REQUIRED_LONG_STRING: str = "[required]"
rich_cfg.REQUIRED_SHORT_STRING: str = ""
rich_cfg.APPEND_METAVARS_HELP_STRING: str = "({})"

rich_cfg.OPTION_GROUPS: dict[str, list[rich_cfg.OptionGroupDict]] = {}

rich_cfg.ERRORS_EPILOGUE = """[bright_black]\
For more info, usage guides, examples, and API documentation,
visit:[/] [link]https://github.com/runsonmymachine/socx[/]
""".strip()

rich_cfg.ERRORS_SUGGESTION: str | rich.text.Text | None = """\
Try running with '-h' or '--help' for more information.
"""
