from __future__ import annotations
from dataclasses import field
from dataclasses import dataclass

from ._meta import _UIDMeta
from ._meta import _SingletonMeta


class SingletonMixin(metaclass=_SingletonMeta):
    """
    Singleton mixin class.

    Extending this class enforces the singleton pattern on a subclass.
    """


@dataclass  # cuz a true alpha man never implements __repr__ themselves
class UIDMixin(metaclass=_UIDMeta):
    """
    Unique instance ID mixin class.

    Extending this class assigns a unique instance id to all instances of the
    extending subclass.
    """

    uid: int = field(
        init=False, default=property(lambda self: _UIDMeta.get_uid(self))
    )


class PtrMixin(UIDMixin):
    """
    Pointer mixin class.

    Extending this class adds the `ref` property to subclass instances and the
    `dref` class method to the subclass.

    Methods
    -------
    ref: int
        A property which returns a unique instance identifier that can be used
        as an argument to `dref` class method in order to retrieve the instance
        of that subclass which corresponds to that identifier.

        Note that the class does not hold any strong references to its
        instances, therefore if the instance was garbage collected before or
        during a call to `dref` then None will be returned.

    dref: PtrMixin
        Given an instance-id of a PtrMixin subclass instance, it will be used
        as a key to a weak-referenced dictionary who's values are handles to
        living instances of that subclass in order to retreive the original
        instance corresponding to the given reference-id.

        Note that if an instance got garbage collected prior or during the call
        to `dref`, None is returned instead of the instance.

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> class Example(PtrMixin):
    >>>     def __init__(self):
    >>>         self.secret_value = rng.bytes(rng.integers(1, 513))
    >>> ...
    >>> instances = [Example() for _ in range(9999999)]
    >>> ...
    >>> def place_secret(secret) -> int:
    >>>     global instances
    >>>     rng.shuffle(instances)
    >>>     unknown = instances[rng.integers(0, len(instances))]
    >>>     unknown.secret = secret
    >>>     secret_key = unknown.ref
    >>>     unknown = None
    >>>     rng.shuffle(instances) # for extra safety
    >>>     return secret_key
    >>> ...
    >>> secret_value = input("Place your secret")
    >>> print("your secret key is: {}".format(place_secret(secret_value)))
    >>> ... # Some time later
    >>> secret_key = input("Enter the secret key: ")
    >>> secret_value = input("Enter the secret value: ")
    >>> if Example.dref(secret_key).secret == secret_value:
    >>>     print("Success!")
    >>> else:
    >>>     print("Incorrect secret! destroying all evidence!")
    >>>     del secrets
    >>>     print("All evidence have been destroyed. Goodbye.")
    """

    @property
    def ref(self) -> int:
        return self.uid

    @classmethod
    def dref(cls, ref: int) -> PtrMixin:
        return _UIDMeta.get_inst(ref)
