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

from .log import log as log
from .console import console as console
from .validators import ConverterValidator as ConverterValidator

from ._config import _to_tree
from ._config import _get_settings

__all__ = (
    "MODULE_PATH",
    "PACKAGE_PATH",
    "SETTINGS_ROOT",
    "SETTINGS_HOME",
    "settings",
    "settings_tree",
)

from ._config import MODULE_PATH as MODULE_PATH
from ._config import PACKAGE_PATH as PACKAGE_PATH
from ._config import SETTINGS_ROOT as SETTINGS_ROOT
from ._config import SETTINGS_HOME as SETTINGS_HOME

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


