# import sqlite3 as sql
import time
import asyncio as aio
from pathlib import Path

import click
from dynaconf.utils.boxing import DynaBox

# from socx import APP_NAME
# from socx import PACKAGE_PATH
# from socx import USER_DATA_DIR
from socx import TestResult
from socx import Regression
from socx import settings
from socx import logger


# def update_db():
#     db_fp = Path(USER_DATA_DIR/f"{APP_NAME}.db").resolve()
#     db_code = Path(
#       PACKAGE_PATH/"templates"/"sql"/f"{APP_NAME}.sql"
#     ).resolve()
#     con = sql.connect(db_fp)
#     cur = con.cursor()
#     cur.executescript(db_code.read_text(encoding="utf-8"))


def _correct_path_in(input_path: str | Path | None = None) -> Path:
    if input_path is None:
        input_path = settings.regression.rerun_failure_history.input
        dir_in: Path = input_path.directory
        file_in: str = input_path.filename
        path_in: Path = Path(dir_in / file_in)
    else:
        path_in: Path = Path(input_path).resolve()
    return path_in


def _correct_paths_out(
    output_path: str | Path | None = None,
) -> tuple[Path, Path]:
    now = time.strftime("%H-%M")
    today = time.strftime("%d-%m-%Y")
    if output_path is None:
        output_path: DynaBox = settings.regression.rerun_failure_history.output
        dir_out: Path = Path(output_path.directory) / today
        fail_out: Path = Path(dir_out / f"{now}_failed.log")
        pass_out: Path = Path(dir_out / f"{now}_passed.log")
    else:
        fail_out: Path = Path(output_path / f"{now}_failed.log")
        pass_out: Path = Path(output_path / f"{now}_passed.log")
    fail_out.parent.mkdir(parents=True, exist_ok=True)
    pass_out.parent.mkdir(parents=True, exist_ok=True)
    return pass_out, fail_out


def _parse_regression(filepath: Path) -> Regression:
    with click.open_file(filepath, mode="r", encoding="utf-8") as file:
        return Regression.from_lines("rgr", tuple(line for line in file))


def _write_result_files(
    fail_out: str | Path,
    pass_out: str | Path,
    regression: Regression,
) -> None:
    with (
        open(fail_out, mode="w", encoding="utf-8") as ff,
        open(pass_out, mode="w", encoding="utf-8") as pf,
    ):
        for test in regression:
            if test.passed:
                pf.write(f"{test.command.line}\n")
            else:
                ff.write(f"{test.command.line}\n")
    logger.debug(f"regression done: {regression}")


async def _run_from_file(
    input: str | Path | None = None,  # noqa: A002
    output: str | Path | None = None,
) -> None:
    path_in = _correct_path_in(input)
    regression = _parse_regression(path_in)
    pass_out, fail_out = _correct_paths_out(output)
    try:
        await regression.start()
    finally:
        _write_result_files(pass_out, fail_out, regression)
