"""
Management of application configuration settings.

Configurations are defined in .toml files located inside the 'config'
directory.

The default configurations are under settings.toml and can be used as a
reference.

Local configurations may be defined in 'settings.local.toml'.

Any local configration have priority over the defaults and will either
override the default, or be merged with it if dynaconf_merge is true,
and the keys do not conflict.

Reference the settings.toml file for an example of how configurations are
defined.

For additional information regarding the internals of this module, reference
dynaconf documentation on its official-site/github-repository.
"""

from __future__ import annotations

from typing import Any
from typing import Final
from pathlib import Path
from weakref import proxy

from rich.tree import Tree
from rich.table import Table
from rich.console import Group
from dynaconf import Dynaconf
from dynaconf import LazySettings
from dynaconf import ValidationError
from dynaconf import add_converter
from dynaconf.validator import empty
from dynaconf.validator import Validator
from dynaconf.utils.boxing import Box
from dynaconf.utils.boxing import DynaBox

from .log import log as log
from .console import console as console
from .validators import ConverterValidator as ConverterValidator

__all__ = (
    "settings",
    "settings_tree",
)

MODULE_PATH: Final[Path] = Path(__file__).resolve()
"""Absolue path to module."""

PACKAGE_PATH: Final[Path] = Path(__spec__.parent).parent.resolve()
"""Absolue path to package root directory."""


def _init_settings() -> Dynaconf:
    log.debug("Settings initialization starting...")
    add_converter("path", lambda x: Path(x).resolve())
    _settings: Dynaconf = Dynaconf(
        envvar_prefix="COVGEN",
        root_path=str(PACKAGE_PATH / "settings"),
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


def settings_tree(
    root: Dynaconf | DynaBox | dict,
    label: str = "Settings",
) -> Tree | Table:
    """Get a tree representation of a dynaconf settings instance."""
    if isinstance(root, Dynaconf):
        root = root.as_dict()
    if not isinstance(root, dict | list | tuple | set):
        root = str(root)
    return _to_tree(label, root)


settings = _get_settings()
"""
Global settings instance.

Any attribute/key accesses to this instance trigger a lazy loading operation
which will attempt to find and read the value of the attribute from any of the
.toml configuration files under the 'settings' directory.
"""


