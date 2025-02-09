from __future__ import annotations

import os as os
import sys as sys
import enum as enum
import typing as t
import dataclasses as dc
import argparse as argparse
from pathlib import Path as Path

import click as click

from .constants import LST_COMMENT_TOKENS as LST_COMMENT_TOKENS
from .constants import LST_FILE_SUFFIXES as LST_FILE_SUFFIXES
from .constants import DEFAULT_INPUT_PATH as DEFAULT_INPUT_PATH
from .constants import DEFAULT_OUTPUT_PATH as DEFAULT_OUTPUT_PATH

from .inout import FileInfo as FileInfo


__all__ = (
    "ASM",
    "Statistics",
    "Instruction",
)


class AddressSpaces:
    """Memory address spaces in ROM/NVM."""

    MCU_ROM = 0x40000000
    """
    Base MCU ROM (Read-Only-Memory) memory adress.
    """

    SPU_ROM = 0x4000D668
    """
    Base SPU ROM (Read-Only-Memory) memory adress.
    """

    HWS_ROM = 0x4000FC00
    """
    Base HWS ROM (Read-Only-Memory) memory adress.
    """

    MCU_NVM = 0x40010000
    """
    Base MCU NVM (Non-Volatile Memory) memory adress.
    """

    HWS_NVM = 0x40010E0C
    """
    Base HWS NVM (Non-Volatile Memory) memory adress.
    """


@dc.dataclass
class Instruction:
    """Represents a single instruction in the list file."""

    func: str
    """
    Symbolic function name.
    """

    addr: int
    """
    Instruction start address in memory segment.
    """

    bytelen: int
    """
    Total byte length in memory.
    """

    # segment: MemorySegment
    """
    Memory segment of the instruction.
    """


@dc.dataclass
class Statistics:
    """Collects statistics on consumed instructions."""

    base_address: int | None = None
    """
    Base address, currently, address of the first parsed instruction.
    """

    max_funcname_len: int | None = None
    """
    Maximum function name character length out of all consumed instructions.
    """

    def consume(self, inst: Instruction) -> None:
        if inst is not None:
            self._update_base_addr(inst)
            self._update_max_funcname_len(inst)

    def _update_base_addr(self, inst: Instruction) -> None:
        if self.base_address is None:
            self.base_address = inst.address

    def _update_max_funcname_len(self, inst: Instruction) -> None:
        fnlen = len(inst.funcname)
        maxlen = self.max_funcname_len
        if maxlen is None or maxlen < fnlen:
            self.max_funcname_len = fnlen


@dc.dataclass
class ASM:
    """An ordered list of assembly instructions read from a file."""

    file: str | Path
    """
    Assembly file name.
    """

    statistics: Statistics = dc.field(init=False, default_factory=Statistics)
    """
    Statistics about the current instruction set.
    """

    instructions: t.Iterable[Instruction] = dc.field(
        init=False, default_factory=list
    )
    """
    Ordered list of assembly instructions parsed from consumed strings.
    """

    def consume(self, inst: Instruction) -> None:
        self.statistics.consume(inst)
        self.instructions.append(inst)
