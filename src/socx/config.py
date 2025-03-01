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

from pathlib import Path

from rich.tree import Tree
from rich.table import Table
from dynaconf import Dynaconf
from dynaconf.utils.boxing import DynaBox

from .decorators import log_it
from ._config import _to_tree
from ._config import _get_settings


__all__ = (
    # API
    "settings",
    "reconfigure",
    "settings_tree",
    # Metadata
    "APP_NAME",
    "APP_AUTHOR",
    "APP_VERSION",
    # Application Paths
    "APP_SETTINGS_DIR",
    "APP_USER_SETTINGS_DIR",
    "APP_SETTINGS_FILE_NAME",
    "APP_SETTINGS_FILE_PATH",
    # Local User Paths
    "USER_LOG_DIR",
    "USER_DATA_DIR",
    "USER_CACHE_DIR",
    "USER_STATE_DIR",
    "USER_CONFIG_DIR",
    "USER_RUNTIME_DIR",
    "USER_LOG_FILE_PATH",
)


from ._config import APP_NAME as APP_NAME
from ._config import APP_AUTHOR as APP_AUTHOR
from ._config import APP_VERSION as APP_VERSION
from ._config import APP_SETTINGS_DIR as APP_SETTINGS_DIR
from ._config import APP_USER_SETTINGS_DIR as APP_USER_SETTINGS_DIR
from ._config import APP_SETTINGS_FILE_NAME as APP_SETTINGS_FILE_NAME
from ._config import APP_SETTINGS_FILE_PATH as APP_SETTINGS_FILE_PATH
from ._config import USER_LOG_DIR as USER_LOG_DIR
from ._config import USER_DATA_DIR as USER_DATA_DIR
from ._config import USER_CACHE_DIR as USER_CACHE_DIR
from ._config import USER_STATE_DIR as USER_STATE_DIR
from ._config import USER_CONFIG_DIR as USER_CONFIG_DIR
from ._config import USER_RUNTIME_DIR as USER_RUNTIME_DIR
from ._config import USER_LOG_FILE_PATH as USER_LOG_FILE_PATH


settings: Dynaconf = _get_settings()
"""
Global settings instance.

Any attribute/key accesses to this instance trigger a lazy loading operation
which will attempt to find and read the value of the attribute from any of the
.toml configuration files under the 'settings' directory.
"""


@log_it
def reconfigure(
    path: Path,
    preload: list[Path | str] | None = None,
    includes: list[Path | str] | None = None,
) -> Dynaconf:
    """Reconfigure the current settings with configurations from path."""
    from ._config import _load_settings

    if isinstance(preload, Path):
        preload = str(preload)
    if isinstance(includes, Path):
        includes = str(includes)
    _load_settings(path, preload, includes)


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
