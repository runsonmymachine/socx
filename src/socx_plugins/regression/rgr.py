# import sqlite3 as sql
import time
import asyncio as aio
from pathlib import Path

import click

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


def write_results(regression):
    now = time.strftime("%H-%M")
    today = time.strftime("%d-%m-%Y")
    spec_out = settings.regression.rerun_failure_history.output
    dir_out: Path = Path(spec_out.directory) / today
    fail_out: Path = dir_out / spec_out.name / f"{now}_fail.log"
    pass_out: Path = dir_out / spec_out.name / f"{now}_pass.log"
    fail_out.parent.mkdir(parents=True, exist_ok=True)
    pass_out.parent.mkdir(parents=True, exist_ok=True)
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


async def rerun_fail_hist():
    spec_in = settings.regression.rerun_failure_history.input
    path_in: Path = Path(spec_in.directory) / spec_in.filename
    logger.debug(f"{spec_in=}")
    with click.open_file(path_in, mode="r", encoding="utf-8") as file:
        regression = Regression.from_lines("rgr", tuple(line for line in file))
    try:
        await regression.start()
    except:
        raise
    # else:
    #     await aio.to_thread(write_results, (regression))
    finally:
        write_results(regression)
