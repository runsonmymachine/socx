from __future__ import annotations

from weakref import WeakValueDictionary
from typing import ClassVar
from threading import RLock


class _SingletonMeta(type):
    """Metaclass for creating singleton mixin classes."""

    __instances: ClassVar[dict[type, type]] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = super().__call__(*args, **kwargs)
        return cls.__instances[cls]


class _UIDMeta(type):
    """Metaclass for creating unique instance id mixin classes."""

    __lock: ClassVar[RLock] = RLock()
    __handles: ClassVar[dict[int, object]] = WeakValueDictionary()
    __uid_map: ClassVar[dict[str, int]] = {}

    def __call__(cls, *args, **kwargs) -> _UIDMeta:
        inst = super().__call__(*args, **kwargs)
        inst.__uid = cls._next_uid(inst)
        cls.__handles[inst.__uid] = inst
        return inst

    @classmethod
    def get_inst(cls, inst_uid: int) -> _UIDMeta:
        return cls.__handles.get(inst_uid)

    def get_uid(cls) -> int:
        return cls.__uid

    def _next_uid(cls, inst) -> int:
        name = inst.__class__.__name__
        with cls.__lock:
            if name not in cls.__uid_map:
                cls.__uid_map[name] = 0
            rv = cls.__uid_map[name]
            cls.__uid_map[name] += 1
        return rv



