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

from rich.tree import Tree
from rich.table import Table
from dynaconf import Dynaconf
from dynaconf.utils.boxing import DynaBox

from ._config import _to_tree
from ._config import _get_settings

__all__ = (
    # API
    "settings",
    "settings_tree",
    # Metadata
    "APPLICATION_NAME",
    "APPLICATION_AUTHOR",
    "APPLICATION_VERSION",
    # Directories
    "APPLICATION_LOG_DIR",
    "APPLICATION_DATA_DIR",
    "APPLICATION_CACHE_DIR",
    "APPLICATION_STATE_DIR",
    "APPLICATION_CONFIG_DIR",
    "APPLICATION_RUNTIME_DIR",
)


from ._config import APPLICATION_NAME as APPLICATION_NAME
from ._config import APPLICATION_AUTHOR as APPLICATION_AUTHOR
from ._config import APPLICATION_VERSION as APPLICATION_VERSION
from ._config import APPLICATION_LOG_DIR as APPLICATION_LOG_DIR
from ._config import APPLICATION_DATA_DIR as APPLICATION_DATA_DIR
from ._config import APPLICATION_CACHE_DIR as APPLICATION_CACHE_DIR
from ._config import APPLICATION_STATE_DIR as APPLICATION_STATE_DIR
from ._config import APPLICATION_CONFIG_DIR as APPLICATION_CONFIG_DIR
from ._config import APPLICATION_RUNTIME_DIR as APPLICATION_RUNTIME_DIR


settings = _get_settings()
"""
Global settings instance.

Any attribute/key accesses to this instance trigger a lazy loading operation
which will attempt to find and read the value of the attribute from any of the
.toml configuration files under the 'settings' directory.
"""


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
