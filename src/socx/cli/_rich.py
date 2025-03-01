import rich_click as click

from ..console import console

class RichHelp(click.RichHelpConfiguration):
    def get_help(self, ctx: click.Context) -> str:
        return self._header(ctx) + super().get_help(ctx) + self._footer(ctx)

    def _header(self, ctx: click.Context) -> str:
        with console.capture() as header:
            console.line()
            console.rule(characters="=")
            console.line()
            console.print("SoCX", justify="center", highlight=True)
            console.print("[b][u]Help & Usage", justify="center")
            console.line()
        return header.get()

    def _footer(self, ctx: click.Context) -> str:
        path_text = "->".join(ctx.command_path.split())
        with console.capture() as footer:
            console.line(2)
            console.print(
                f"[bright_black](help: {path_text})", justify="center"
            )
            console.rule(characters="=")
        return footer.get()


class RichGroup(RichHelp, click.Group):
    def group(self, *args, **kwargs) -> click.RichGroup:
        kwargs["cls"] = RichGroup
        return super().group(*args, **kwargs)

    def command(self, *args, **kwargs) -> click.RichCommand:
        kwargs["cls"] = RichCommand
        return super().command(*args, **kwargs)


class RichCommand(RichHelp, click.Command):
    pass



