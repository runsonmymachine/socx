from functools import partial

import rich_click as click


input_opt: click.Option = partial(
    click.option,
    "-i",
    "--input",
    nargs=1,
    metavar="FILE",
    required=False,
    help="Input file of failed commands to rerun",
)

output_opt: click.Option = partial(
    click.option,
    "-o",
    "--output",
    nargs=1,
    metavar="DIRECTORY",
    required=False,
    help="Output directory for writing passed/failed run commands.",
)
