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

import typing as t
import pathlib as pathlib

import dynaconf as dynaconf
import dynaconf.validator as vld

from .validators import ConverterValidator as ConverterValidator

MODULE_PATH: t.Final[pathlib.Path] = pathlib.Path(__file__).resolve()
"""
Absolue path to module.
"""


PACKAGE_PATH: t.Final[pathlib.Path] = (
    # <package>/src/covgen/config.py --> ../../.. --> <package>
    pathlib.Path(__spec__.parent).parent.resolve()
)
"""
Absolue path to package directory path.
"""


dynaconf.add_converter("path", lambda x: pathlib.Path(x).resolve())

settings: dynaconf.LazySettings = dynaconf.Dynaconf(
    envvar_prefix="COVGEN",
    environments=False,
    load_dotenv=True,
    root_path=str(PACKAGE_PATH / "settings"),
    validators=[
        vld.Validator(
            "converter.source",
            condition=ConverterValidator.source_validator,
            must_exist=True,
        ),
        vld.Validator(
            "converter.target",
            condition=ConverterValidator.target_validator,
            must_exist=True,
        ),
        # vld.Validator(
        #     ("converter.source", "converter.includes", "converter.excludes"),
        #     condition=ConverterValidator.includes_validator,
        #     must_exist=True,
        # ),
    ],
    settings_file=["converter.toml", "filetypes.toml", "plugins.toml"],
)
"""
Settings handling, and io representation as python object.
"""

try:
    settings.validators.validate_all()
except dynaconf.DynaconfParseError as e:
    accumulative_errors = e.details
