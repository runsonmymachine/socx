from __future__ import annotations

from weakref import WeakValueDictionary
from typing import ClassVar
from threading import RLock


class _UIDMeta(type):
    __lock: ClassVar[RLock] = RLock()
    __uid_map: ClassVar[dict[str, int]] = {}
    __handles: ClassVar[dict[int, object]] = WeakValueDictionary()

    def __call__(cls, *args, **kwargs) -> _UIDMeta:
        inst = super().__call__(*args, **kwargs)
        inst.__uid = cls._next_uid(inst)
        cls.__handles[inst.__uid] = inst
        return inst

    def ref(cls) -> _UIDMeta:
        return cls.__uid

    @classmethod
    def dref(cls, handle) -> _UIDMeta:
        return cls.__handles.get(handle)

    def _next_uid(cls, inst) -> int:
        name = inst.__class__.__name__
        with cls.__lock:
            if name not in cls.__uid_map:
                cls.__uid_map[name] = 0
            rv = cls.__uid_map[name]
            cls.__uid_map[name] += 1
        return rv



