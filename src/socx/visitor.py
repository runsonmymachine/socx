from __future__ import annotations

from typing import Protocol


class Node[NODE](Protocol):
    def accept(self, v: Visitor[NODE]) -> None:
        """Accept a visit from a visitor."""
        ...


class Visitor[NODE](Protocol):
    def visit(self, n: NODE) -> None:
        """Visit a node."""
        ...


class Structure[NODE](Protocol):
    def children(self) -> list[NODE]:
        """Retrieve the immediate child nodes of a structure."""
        ...


class Proxy[NODE](Protocol):
    def children(self, n: NODE) -> list[NODE]:
        """Retrieve the immediate children of a node in a structure."""
        ...


class Adapter[NODE](Protocol):
    def accept(self, n: NODE, v: Visitor[NODE], p: Proxy[NODE]) -> None:
        """Adapt a visitor to visit a structure of nodes through a proxy."""
        ...


class TopDownTraversal[NODE](Adapter):
    def accept(self, n: NODE, v: Visitor[NODE], p: Proxy[NODE]) -> None:
        n.accept(v)
        for c in p.children(v):
            self.accept(c, v, p)


class BottomUpTraversal[NODE](Adapter):
    def accept(self, n: NODE, v: Visitor[NODE], p: Proxy[NODE]) -> None:
        for c in p.children(v):
            self.accept(c, v, p)
        v.visit(n)


class ByLevelTraversal[NODE](Adapter[NODE]):
    def accept(self, n: NODE, v: Visitor[NODE], p: Proxy[NODE]) -> None:
        q = [n]
        while q:
            t = []
            for n_ in q:
                v.visit(n_)
                t.extend(p.children(n_))
            q = t
