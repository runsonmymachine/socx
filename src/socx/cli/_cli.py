from types import CodeType

import rich_click as click
from dynaconf.utils.boxing import DynaBox

from ..config import settings
from ..decorators import log_it


_CONTEXT_SETTINGS = dict(
    help_option_names=["-h", "--help"],
)


class CmdLine(click.RichMultiCommand, click.Group):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("context_settings", _CONTEXT_SETTINGS)
        click.RichMultiCommand.__init__(self, *args, **kwargs)
        click.Group.__init__(self, *args, **kwargs)
        self._plugins = {}

    @property
    @log_it
    def plugins(self):
        """The plugins property."""
        if not self._plugins:
            self._load_plugins()
        return self._plugins

    @property
    @log_it
    def plugin_names(self) -> list[str]:
        return [plugin.name for plugin in self.plugins]

    @log_it
    def list_commands(self, ctx) -> list[str]:
        rv = list(self.plugins.values())
        rv += super().list_commands(ctx)
        rv = list(filter(lambda x: isinstance(x, str), rv))
        rv.sort(reverse=True)
        return rv

    @log_it
    def get_command(self, ctx: click.Context, name: str) -> CodeType:
        if name in self.plugins:
            rv = self.plugins[name]
        else:
            rv = super().get_command(ctx, name)
        return rv

    @log_it
    def _load_plugins(self) -> None:
        plugins = settings.plugins
        for name in settings.plugins:
            plugin = plugins[name]
            self._load_plugin(plugin)

    @log_it
    def _load_plugin(self, plugin: DynaBox) -> click.Command:
        ns = {}
        code = self._compile(plugin.path, plugin.name)
        eval(code, ns, ns)
        cmd = ns.get("cli")
        if cmd is None:
            self._plugin_error(plugin.name)
        self._plugins[plugin.name] = cmd
        self.add_command(cmd, plugin.name)

    @classmethod
    @log_it
    def _unique(cls, args: str | list | tuple | set) -> list:
        lookup = set()
        args = cls._listify(args)
        args = [
            x for x in args if args not in lookup and lookup.add(x) is None
        ]
        return args

    @classmethod
    @log_it
    def _listify(cls, args: str | list | tuple | set | dict) -> list:
        if isinstance(args, list):
            rv = args
        elif isinstance(args, dict):
            rv = list(args.values())
        elif isinstance(args, set | tuple):
            rv = list(args)
        else:
            rv = [args]
        return rv

    @classmethod
    def _compile(cls, file, name):
        code = compile(file.read_text(), name, "exec")
        return code

    @classmethod
    @log_it
    def _plugin_error(cls, name) -> None:
        err = f"""
        failed to load plugin '{name}'
        please ensure the correctness of the plugin's path configuration
        and that 'cli' function is properly defined (usual definition is done
        by applying the @click.group() or @click.command() decorator to the
        function.
        """
        exc = ValueError(err)
        raise exc
