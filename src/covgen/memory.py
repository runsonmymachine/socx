from __future__ import annotations

import typing as t
import dataclasses as dc

import rich as rich
import rich.table as table


@dc.dataclass(frozen=True)
class MemorySegment:
    origin: int
    """
    Origin/Base address of the address space.
    """

    length: int
    """
    Length/Size of the address space in bytes.
    """

    end: int
    """
    End/Highest memory address of the address space.
    """


@dc.dataclass(frozen=True)
class DynamicSymbol:
    name: str
    """
    Name identifier aliased with the symbol.
    """

    addr: int
    """
    Symbol start address in the relevant address space.
    """

    length: int
    """
    Total byte length symbol takes up in memory address space.
    """

    index: int
    """
    Index of symbol in symbol table.
    """


@dc.dataclass
class SymbolTable(t.TypedDict):
    device: str
    """
    Name identifier of the device associated with the address space.
    """

    segment: MemorySegment
    """
    Address space memory adress specification.
    """

    symbols: tuple[DynamicSymbol, ...] | None = None
    """
    Tuple listing of all dynamic symbols associated with the device and their
    mapping within the address space.
    """


@table.dataclass
class RichSymTable:
    device: str
    """
    Name identifier of the device associated with the address space.
    """

    segment: MemorySegment
    """
    Address space memory adress specification.
    """

    symbols: tuple[DynamicSymbol, ...] | None = None
    """
    Tuple listing of all dynamic symbols associated with the device and their
    mapping within the address space.
    """
