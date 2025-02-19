from __future__ import annotations

import sys
from typing import Any
from typing import Final
from pathlib import Path
from importlib.metadata import version
from importlib.metadata import metadata
from importlib.metadata import PackageMetadata
from collections.abc import Iterable

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
from platformdirs import site_data_dir
from platformdirs import site_cache_dir
from platformdirs import site_config_dir
from platformdirs import site_runtime_dir
from platformdirs import user_log_dir
from platformdirs import user_data_dir
from platformdirs import user_state_dir
from platformdirs import user_cache_dir
from platformdirs import user_config_dir
from platformdirs import user_runtime_dir

from ..log import logger
from ..log import add_handler
from ..log import DEFAULT_LEVEL
from ..log import DEFAULT_TIME_FORMAT
from ..validators import PathValidator


__author__ = "Sagi Kimhi <sagi.kim5@gmail.com>"

__version__ = version(__package__.partition(".")[0])

__metadata__ = metadata(__package__.partition(".")[0])


PACKAGE_NAME: Final[str] = __package__.partition(".")[0]
"""Package name."""

PACKAGE_PATH: Final[Path] = Path(sys.modules[PACKAGE_NAME].__file__).parent
"""Absolute path to package."""

PACKAGE_AUTHOR: Final[str] = __author__
"""Package author."""

PACKAGE_VERSION: Final[str] = __version__
"""Package version."""

PACKAGE_METADATA: Final[PackageMetadata] = __metadata__
"""Package metadata."""

APP_NAME: Final[str] = PACKAGE_NAME
"""Application name."""

APP_AUTHOR: Final[str] = PACKAGE_METADATA
"""Application author"""

APP_VERSION: Final[str] = PACKAGE_VERSION
"""Application version."""

SITE_DATA_DIR: Final[Path] = Path(
    site_data_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=False,
    )
).resolve()
"""Absolute path to platform's native application data directory."""

SITE_CACHE_DIR: Final[Path] = Path(
    site_cache_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=False,
    )
).resolve()
"""Absolute path to platform's native application cache directory."""

SITE_CONFIG_DIR: Final[Path] = Path(
    site_config_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=False,
    )
).resolve()
"""Absolute path to platform's native application config directory."""

SITE_RUNTIME_DIR: Final[Path] = Path(
    site_runtime_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=False,
    )
).resolve()
"""Absolute path to platform's native application runtime directory."""

USER_LOG_DIR: Final[Path] = Path(
    user_log_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=True,
    )
)
"""Absolute path to platform's native application logs directory."""

USER_DATA_DIR: Final[Path] = Path(
    user_data_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application data directory."""

USER_CACHE_DIR: Final[Path] = Path(
    user_cache_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application cache directory."""

USER_STATE_DIR: Final[Path] = Path(
    user_state_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application state directory."""

USER_CONFIG_DIR: Final[Path] = Path(
    user_config_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application config directory."""

USER_RUNTIME_DIR: Final[Path] = Path(
    user_runtime_dir(
        appname=APP_NAME,
        version=APP_VERSION,
        appauthor=APP_AUTHOR,
        ensure_exists=True,
    )
).resolve()
"""Absolute path to platform's native application runtime directory."""

_init_done: bool = False

_settings: Dynaconf | dict = {
    name: value for name, value in vars().items() if not name.startswith("_")
}

_user_log: Path = USER_LOG_DIR / "run.log"

_static_dir: Path = Path(PACKAGE_PATH) / "static" / "toml"

_static_file: Path = "settings.toml"

_user_settings: Path = Path(USER_CONFIG_DIR) / "settings.toml"

_static_settings: Path = Path(_static_dir) / _static_file

_settings_kwargs = dict(
    encoding="utf-8",
    lowercase_read=True,
    envvar_prefix=APP_NAME.upper(),
    load_dotenv=True,
    environments=False,
    dotenv_override=True,
    sysenv_fallback=True,
    validate_on_update="all",
    validators=[Validator(r"convert.*", ne=empty)],
)


def _init_module() -> None:
    global _init_done
    logger.debug("initializing module.")
    _init_logger()
    _init_converters()
    _load_settings()
    _validate_settings()
    _init_done = True
    logger.debug("module initialized.")


def _init_logger() -> None:
    global logger
    logger.debug("initializing logger.")
    add_handler(
        RichHandler(
            level=DEFAULT_LEVEL,
            console=Console(
                file=open_file(
                    filename=str(_user_log),
                    mode="w",
                    encoding="utf-8",
                    lazy=True,
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
    logger.info("logging initialized.")
    logger.info(f"logging at path: {_user_log}")


def _init_converters() -> None:
    logger.debug("initializing settings converters.")
    add_converter("path", lambda x: Path(str(x)).resolve())
    add_converter("glob", lambda x: next(Path().glob(x)).resolve())
    logger.debug("settings converters initialized.")


def _load_settings(
    path: Path | None = None,
    preload: Iterable[str] | None = None,
    includes: Iterable[str] | None = None,
) -> Dynaconf:
    global _settings
    path = path if path else _static_settings
    preload = preload if preload else []
    includes = includes if includes else []
    logger.debug(f"loading settings from {path}.")
    settings = Dynaconf(
        root_path=path.parent,
        preload=preload,
        settings_files=[str(path)],
        includes=includes,
        **_settings_kwargs,
        **_settings.as_dict() if isinstance(_settings, Dynaconf) else _settings,
    )
    settings.update(_settings)
    _settings = settings
    logger.debug("settings loaded.")
    return _settings


def _validate_settings() -> None:
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
    if not _init_done:
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
