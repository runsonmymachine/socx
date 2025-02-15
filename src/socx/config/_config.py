from __future__ import annotations

import logging
import shutil
from weakref import proxy
from typing import Any
from typing import Final
from pathlib import Path
from importlib import resources
from importlib.metadata import version
from importlib.metadata import metadata
from importlib.metadata import PackageMetadata

from click import open_file
from rich.tree import Tree
from rich.table import Table
from rich.console import Group
from rich.console import Console
from rich.logging import RichHandler
from dynaconf import Dynaconf
from dynaconf import ValidationError
from dynaconf import add_converter
from dynaconf.validator import empty
from dynaconf.validator import Validator
from platformdirs import user_log_dir
from platformdirs import user_data_dir
from platformdirs import user_state_dir
from platformdirs import user_cache_dir
from platformdirs import user_config_dir
from platformdirs import user_runtime_dir

from ..log import logger
from ..log import get_logger
from ..log import add_handler
from ..log import DEFAULT_LEVEL
from ..log import DEFAULT_FORMAT
from ..log import DEFAULT_TIME_FORMAT
from ..validators import PathValidator


__author__ = "Sagi Kimhi <sagi.kim5@gmail.com>"

__version__ = version(__package__.partition(".")[0])

__metadata__ = metadata(__package__.partition(".")[0])


PACKAGE_NAME: Final[str] = __package__.partition(".")[0]
"""Package name."""

PACKAGE_PATH: Final[Path] = Path(__file__).parents[1].resolve()
"""Absolute path to package."""

PACKAGE_AUTHOR: Final[str] = __author__
"""Package author."""

PACKAGE_VERSION: Final[str] = __version__
"""Package version."""

PACKAGE_METADATA: Final[PackageMetadata] = __metadata__
"""Package metadata."""

APPLICATION_NAME: Final[str] = PACKAGE_NAME
"""Application name."""

APPLICATION_AUTHOR: Final[str] = PACKAGE_METADATA
"""Application author"""

APPLICATION_VERSION: Final[str] = PACKAGE_VERSION
"""Application version."""

APPLICATION_LOG_DIR: Final[Path] = Path(
    user_log_dir(
        appname=APPLICATION_NAME,
        version=APPLICATION_VERSION,
        appauthor=APPLICATION_AUTHOR,
        ensure_exists=True,
    )
)
"""Absolute path to platform's native application logs directory."""

APPLICATION_DATA_DIR: Final[Path] = Path(
    user_data_dir(
        appname=APPLICATION_NAME,
        version=APPLICATION_VERSION,
        appauthor=APPLICATION_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application data directory."""

APPLICATION_CACHE_DIR: Final[Path] = Path(
    user_cache_dir(
        appname=APPLICATION_NAME,
        version=APPLICATION_VERSION,
        appauthor=APPLICATION_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application cache directory."""

APPLICATION_STATE_DIR: Final[Path] = Path(
    user_state_dir(
        appname=APPLICATION_NAME,
        version=APPLICATION_VERSION,
        appauthor=APPLICATION_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application state directory."""

APPLICATION_CONFIG_DIR: Final[Path] = Path(
    user_config_dir(
        appname=APPLICATION_NAME,
        version=APPLICATION_VERSION,
        appauthor=APPLICATION_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application config directory."""

APPLICATION_RUNTIME_DIR: Final[Path] = Path(
    user_runtime_dir(
        appname=APPLICATION_NAME,
        version=APPLICATION_VERSION,
        appauthor=APPLICATION_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application runtime directory."""

_log: Path = Path(APPLICATION_LOG_DIR / "run").with_suffix(".log")

_settings: Dynaconf | None = None

_initialized: bool = False

_settings_root: Path = Path(PACKAGE_PATH / "static" / "toml").resolve()


def _init_module() -> None:
    global _initialized
    logger.debug("Initializing module.")
    _init_logger()
    _init_dynaconf()
    _init_config_files()
    _init_user_settings()
    _validate_dynaconf_settings()
    _initialized = True
    logger.debug("Module initialized.")


def _init_logger() -> None:
    global logger
    logger.debug("Initializing logger.")
    add_handler(
        RichHandler(
            level=DEFAULT_LEVEL,
            console=Console(
                file=open_file(
                    filename=str(_log), mode="w", encoding="utf-8", lazy=True
                ),
                tab_size=4,
                width=110,
            ),
            markup=False,
            show_time=True,
            show_level=True,
            rich_tracebacks=True,
            locals_max_string=None,
            locals_max_length=None,
            tracebacks_theme="monokai",
            omit_repeated_times=False,
            tracebacks_word_wrap=False,
            tracebacks_show_locals=True,
            log_time_format=DEFAULT_TIME_FORMAT,
        )
    )
    logger.debug("Logging initialized.")
    logger.debug(f"Logging at path: {_log}")


def _init_dynaconf() -> None:
    logger.debug("Initializing dynaconf.")
    add_converter("path", lambda x: Path(str(x)).resolve())
    add_converter("glob", lambda x: next(Path().glob(x)).resolve())
    logger.debug("Dynaconf initialized.")


def _init_config_files() -> None:
    logger.debug("Initializing user config files.")
    for config_file in _settings_root.glob("*.toml"):
        user_config_file = Path(APPLICATION_CONFIG_DIR / config_file.name)
        if not user_config_file.exists():
            logger.debug(
                "user config file not found, "
                f"writing default config file: '{user_config_file.name}'..."
            )
            user_config_file.write_text(config_file.read_text())
            logger.debug(
                f"config file succesfuly written to {user_config_file}."
            )
    logger.debug("User config files initialized.")


def _init_user_settings() -> Dynaconf:
    global _settings
    logger.debug("Initializing settings.")
    _settings = Dynaconf(
        root_path=str(APPLICATION_CONFIG_DIR),
        settings_files=["settings.toml"],
        envvar_prefix=APPLICATION_NAME.upper(),
        load_dotenv=False,
        environments=False,
        dotenv_override=False,
        sysenv_fallback=True,
        validate_on_update="all",
        validators=[Validator(r"convert.*", ne=empty)],
    )
    _settings.update({
        "PACKAGE_NAME": PACKAGE_NAME,
        "PACKAGE_PATH": PACKAGE_PATH,
        "PACKAGE_AUTHOR": PACKAGE_AUTHOR,
        "PACKAGE_VERSION": PACKAGE_VERSION,
        "APPLICATION_NAME": APPLICATION_NAME,
        "APPLICATION_AUTHOR": APPLICATION_AUTHOR,
        "APPLICATION_VERSION": APPLICATION_VERSION,
        "APPLICATION_LOG_DIR": APPLICATION_LOG_DIR,
        "APPLICATION_DATA_DIR": APPLICATION_DATA_DIR,
        "APPLICATION_CACHE_DIR": APPLICATION_CACHE_DIR,
        "APPLICATION_STATE_DIR": APPLICATION_STATE_DIR,
        "APPLICATION_CONFIG_DIR": APPLICATION_CONFIG_DIR,
        "APPLICATION_RUNTIME_DIR": APPLICATION_RUNTIME_DIR,
    })
    logger.debug("Settings initialized.")


def _validate_dynaconf_settings() -> None:
    global _settings
    logger.debug("Validating settings.")
    for lang in _settings.convert:
        _settings.validators.register(_get_convert_validators(lang))
    accumulative_errors = ""
    try:
        _settings.validators.validate_all()
    except ValidationError as e:
        accumulative_errors = e.details
        logger.debug("Settings validation failed.")
    else:
        logger.debug("Settings validation passed.")
    finally:
        if accumulative_errors:
            errors = ValidationError(accumulative_errors)
            logger.exception(accumulative_errors, exc_info=errors)


def _get_settings() -> Dynaconf:
    if not _initialized:
        _init_module()
    return _settings


def _get_convert_validators(lang: str) -> list[Validator]:
    (
        Validator(
            f"convert.{lang}.source",
            condition=PathValidator.source_validator,
            must_exist=True,
            ne=empty,
        ),
    )
    (
        Validator(
            f"convert.{lang}.target",
            condition=PathValidator.target_validator,
            must_exist=True,
            ne=empty,
        ),
    )


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
