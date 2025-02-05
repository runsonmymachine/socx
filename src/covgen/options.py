from __future__ import annotations

import typing as t
import pathlib as pathlib
import functools as fun

import click as click

from . import config as cfg

input_: t.Final[click.Option] = fun.partial(
    click.option,
    "-i",
    "--input",
    expose_value=True,
    type=click.Path(
        exists=True,
        readable=True,
        dir_okay=True,
        file_okay=True,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
    envvar="COVGEN_INPUT_PATH",
    allow_from_autoenv=True,
    help=(
        "Path to input lst file or directory with multiple lst files "
        "from which the tool should generate the coverage."
    ),
)

output: t.Final[click.Option] = fun.partial(
    click.option,
    "-o",
    "--output",
    expose_value=True,
    type=click.Path(
        exists=False,
        writable=True,
        dir_okay=True,
        file_okay=False,
        allow_dash=True,
        path_type=pathlib.Path,
    ),
    envvar="COVGEN_OUTPUT_PATH",
    allow_from_autoenv=True,
    help=(
        "Path to output directory to which the generated coverage code "
        "will be written."
    ),
)

indent = fun.partial(
    click.option,
    "-I",
    "--indent",
    default=4,
    expose_value=True,
    type=click.INT,
    show_default=True,
    allow_from_autoenv=True,
    envvar="COVGEN_INDENT_WIDTH",
    help="Tab indentation width (number of spaces per Tab character)",
)
