from __future__ import annotations

from typing import Any
from typing import Final
from pathlib import Path

from rich.tree import Tree
from rich.table import Table
from rich.console import Group
from click import get_app_dir
from dynaconf import Dynaconf
from dynaconf import ValidationError
from dynaconf import add_converter
from dynaconf.validator import empty
from dynaconf.validator import Validator

from .log import log as log
from .console import console as console
from .validators import ConverterValidator as ConverterValidator


MODULE_PATH: Final[Path] = Path(__file__).resolve()
"""Absolue path to module."""


PACKAGE_PATH: Final[Path] = Path(__spec__.parent).parent.resolve()
"""Absolue path to package root directory."""


SETTINGS_ROOT: Final[Path] = Path(PACKAGE_PATH / "settings").resolve()
"""Absolute path to application's global settings directory."""


SETTINGS_HOME: Final[Path] = (Path(get_app_dir("covgen")) / "settings").resolve()
"""Absolute path to application's local user settings directory."""


def _init_settings() -> Dynaconf:
    log.debug("Settings initialization starting...")
    add_converter("path", lambda x: Path(x).resolve())
    _settings: Dynaconf = Dynaconf(
        envvar_prefix="COVGEN",
        root_path=str(SETTINGS_ROOT),
        settings_file=["convert.toml", "filetypes.toml", "plugins.toml"],
        load_dotenv=True,
        environments=False,
        validate_on_update=True,
        validators=[Validator(r"convert.*", nq=empty)],
    )
    log.debug("Settings initialization done.")
    return _settings


def _validate_settings(_settings: Dynaconf) -> None:
    accumulative_errors = ""
    log.debug("Settings validation starting...")
    try:
        for converter_type in _settings.convert:
            _settings.validators.register(
                Validator(
                    f"convert.{converter_type}.source",
                    condition=ConverterValidator.source_validator,
                    must_exist=True,
                ),
                Validator(
                    f"convert.{converter_type}.target",
                    condition=ConverterValidator.target_validator,
                    must_exist=True,
                ),
                # Validator(
                #     (
                #         f"convert.{converter_type}.source",
                #         f"convert.{converter_type}.includes",
                #         f"convert.{converter_type}.excludes",
                #     ),
                #     condition=ConverterValidator.includes_validator,
                #     must_exist=True,
                # ),
            )
        _settings.validators.validate_all()
    except ValidationError as e:
        accumulative_errors = e.details
        log.debug("Settings validation failed.", log_locals=True)
        log.debug(f"Failing configuration values:\n{accumulative_errors}")
        log.debug(f"Accumulated validation errors:\n{accumulative_errors}")
    else:
        log.debug("Settings validation passed.", log_locals=True)
    finally:
        log.debug("Settings validation done.", log_locals=True)


def _get_settings() -> Dynaconf:
    _settings = _init_settings()
    _validate_settings(_settings)
    return _settings


def _to_tree(key: str, val: Any) -> Tree | Table:
    if isinstance(val, list | set | tuple):
        node = Tree(key)
        for i, v in enumerate(val):
            k = f"{key}[{i}]"
            if isinstance(v, dict):
                node.add(Group(k, _to_table("", v)))
            else:
                node.add(_to_table(k, v))
    elif isinstance(val, dict):
        node = Tree(key)
        for k, v in val.items():
            node.add(_to_tree(k, v))
    else:
        node = _to_table(key, str(val))
    return node


def _to_table(key: str, val: Any) -> Table:
    node = Table()
    node.show_lines = True
    node.show_header = True
    node.show_footer = False
    if isinstance(val, list | tuple | set):
        node.add_column("index")
        node.add_column(key)
        for i, v in enumerate(val):
            node.add_row(str(i), str(v))
    elif isinstance(val, dict):
        for k in val:
            node.add_column(k)
        node.add_row(*[str(v) for v in val.values()])
    else:
        node.add_column(str(key))
        node.add_row(str(val))
    return node

