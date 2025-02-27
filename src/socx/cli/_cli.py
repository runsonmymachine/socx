import rich_click as click

from types import CodeType

from ..log import logger
from ..config import settings
from ._rich import RichGroup


_CONTEXT_SETTINGS = dict(
    help_option_names=[
        "?",
        "-h",
        "--help",
    ],
)


class CmdLine(RichGroup, click.Group):
    def __init__(self, *args, **kwargs):
        kwargs["context_settings"] = _CONTEXT_SETTINGS
        super().__init__(*args, **kwargs)
        self._plugins = None

    @property
    def plugins(self) -> list[click.Command]:
        if self._plugins is None:
            self._load_plugins()
        return self._plugins

    @property
    def plugin_names(self) -> list[str]:
        return [cmd.name for cmd in self.plugins.values()]

    def get_command(self, ctx: click.Context, name: str) -> CodeType:
        logger.debug(f"get_command({ctx=}, {name=}) was called...")
        if name in self.plugins and self.plugins[name] is not None:
            rv = self.plugins[name]
            logger.debug(
                f"get_command({ctx=}, {name=}) returning plugin {rv=}."
            )
            return rv
        rv = super().get_command(ctx, name)
        logger.debug(f"get_command({ctx=}, {name=}) returning command {rv=}.")
        return rv

    def list_commands(self, ctx) -> list[str]:
        logger.debug(f"list_commands({ctx=}) was called...")
        rv = list(self.plugins.values())
        rv += super().list_commands(ctx)
        logger.debug(f"list_commands({ctx=}) returning {rv=}.")
        return rv

    @classmethod
    def _listify(cls, args: str | list | tuple | set | dict) -> list:
        logger.debug(f"{cls.__name__}._listify called with {args=}")
        if isinstance(args, list):
            rv = args
        elif isinstance(args, dict):
            rv = list(args.values())
        elif isinstance(args, set | tuple):
            rv = list(args)
        else:
            rv = [args]
        logger.debug(f"{cls.__name__}._listify returning value '{rv=}'")
        return rv

    @classmethod
    def _unique(cls, args: str | list | tuple | set) -> list:
        logger.debug(f"{cls.__name__}._unique called with {args=}")
        lookup = set()
        args = cls._listify(args)
        args = [
            x for x in args if args not in lookup and lookup.add(x) is None
        ]
        logger.debug(f"{cls.__name__}._unique returning {args=}")

    @classmethod
    def _compile(cls, file, name):
        logger.debug(f"{cls.__name__}._compile called with {file=}, {name=}")
        ns = {}
        logger.debug(f"compiling '{name}' (plugin: {file})...")
        code = compile(file.read_text(), name, "exec")
        logger.debug(f"'{name}' compiled.")
        eval(code, ns, ns)
        logger.debug(f"'{name}' evaluated.")
        plugin = ns.get("cli")
        if plugin:
            logger.debug(f"'{name}' loaded.")
            logger.debug(f"{cls.__name__}._compile returning {plugin=}")
            return plugin
        cls._missing_cli_err(name)
        return None

    def _load_plugins(self) -> None:
        if self._plugins is None:
            self._plugins = {}
        else:
            self._plugins.clear()
        for name, path in settings.plugins.items():
            cmd = self._compile(path, name)
            self._plugins[name] = cmd
        for name, cmd in self._plugins.items():
            self.add_command(cmd, name)

    @classmethod
    def _missing_cli_err(cls, name) -> None:
        err = (
            f"failed to load '{name}' (plugin).\n"
            "please make ensure that function 'cli' is defined and has "
            "either @group or @command decorator applied."
        )
        exc = ValueError(err)
        logger.exception(err, exc_info=exc)
        logger.debug(f"'{name}' (plugin) unloaded", exc_info=exc)
