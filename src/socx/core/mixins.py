from __future__ import annotations
from dataclasses import field
from dataclasses import dataclass

from ._uid import _UIDMeta


class PtrMixin(metaclass=_UIDMeta):
    """
    It is probably very unsafe in context of software-security, use this
    for ez compute and lazy eval but using it in an object that also encrypts
    ur password would probably be a rly bad idea.

    Anyway I dont even think I need this I just thought it would be cool to
    write so I did lol.
    """

    @property
    def ref(self) -> int:
        return _UIDMeta.ref(self)

    @classmethod
    def dref(cls, ref: int) -> PtrMixin:
        return _UIDMeta.dref(ref)


@dataclass  # cuz a true alpha man never implements __repr__ themselves
class UIDMixin(PtrMixin):
    """
    A mixin class that generates unique instance ids for instances of the same
    class.
    """

    uid: int = field(init=False, default=property(lambda self: self.ref))
