import typing as t
import dataclasses as dc


@dc.dataclass
class Converter:
    def convert(self, tokens: t.Any) -> None:
        pass
