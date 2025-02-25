from __future__ import annotations

from typing import Protocol
from collections.abc import Iterable


__all__ = (
    "Node",
    "Proxy",
    "Adapter",
    "Visitor",
    "Structure",
    "TopDownTraversal",
    "BottomUpTraversal",
    "ByLevelTraversal",
)


class Node[NODE](Protocol):
    __slots__ = ()

    def accept(self, v: Visitor[Node]) -> None:
        """Accept a visit from a visitor."""
        ...


class Visitor[NODE](Protocol):
    __slots__ = ()

    def visit(self, n: NODE) -> None:
        """Visit a node."""
        ...


class Structure[NODE](Iterable[Node]):
    __slots__ = ()

    def accept(self, v: Visitor[NODE]) -> None:
        """Accept a visit from a visitor."""
        ...

    def children(self) -> list[NODE]:
        """Retrieve the immediate child nodes of a structure."""
        ...


class Proxy[NODE](Protocol):
    __slots__ = ()

    def children(self, n: NODE) -> list[NODE]:
        """Retrieve the immediate children of a node in a structure."""
        ...


class Adapter[NODE](Protocol):
    __slots__ = ()

    def accept(self, n: NODE, v: Visitor[NODE], p: Proxy[NODE]) -> None:
        """Adapt a visitor to visit a structure of nodes through a proxy."""
        ...


class TopDownTraversal(Adapter[Node]):
    def accept(self, n: Node, v: Visitor[Node], p: Proxy[Node]) -> None:
        n.accept(v)
        for c in p.children(v):
            self.accept(c, v, p)


class BottomUpTraversal[Node](Adapter[Node]):
    def accept(self, n: Node, v: Visitor[Node], p: Proxy[Node]) -> None:
        for c in p.children(v):
            self.accept(c, v, p)
        v.visit(n)


class ByLevelTraversal[Node](Adapter[Node]):
    def accept(self, n: Node, v: Visitor[Node], p: Proxy[Node]) -> None:
        q = [n]
        while q:
            t = []
            for n_ in q:
                v.visit(n_)
                t.extend(p.children(n_))
            q = t
