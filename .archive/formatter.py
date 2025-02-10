# -----------------------------------------------------------------------------
# In:
#   0x4000fc00 HwsRomNetInit 18 0
#
# Out:
#   bins HwsRomNetInit = {[
#       (('h4000_fc00 - 'h4000_fc00) >> 1     ) :
#       (('h4000_fc00 - 'h4000_fc00 + 18) >> 1) - 1
#   ]};
#
# In:
#   0x4000fc12 HwsRomFlowFSMPowerupB2B 8 9
#
# Out:
#   bins HwsRomFlowFSMPowerupB2B = {[
#       (('h4000_fc12-'h4000_fc00   ) >> 1) :
#       (('h4000_fc12-'h4000_fc00+ 8) >> 1) - 1
#   ]};
# -----------------------------------------------------------------------------

from __future__ import annotations

import os as os
import sys as sys
import abc as abc
import argparse as argparse
from pathlib import Path as Path

from .constants import LST_FILE_SUFFIXES as LST_FILE_SUFFIXES
from .constants import DEFAULT_INPUT_PATH as DEFAULT_INPUT_PATH
from .constants import DEFAULT_OUTPUT_PATH as DEFAULT_OUTPUT_PATH

from .asm import ASM as ASM
from .asm import Statistics as Statistics
from .asm import Instruction as Instruction


__all__ = (
    "Formatter",
    "SVCoverpoint",
    "LstLine",
)


class Formatter[T](abc.ABC):
    """Format an object of type T to a user defined string format."""

    @classmethod
    @abc.abstractmethod
    def fmt(cls, obj: T, *args, **kwargs) -> str: ...


class LstLine(Formatter[Instruction]):
    """
    Convert an instruction to its corresponding SystemVerilog covergroup
    representation string.
    """

    @classmethod
    def fmt(cls, inst: Instruction, *args, **kwargs) -> str:
        return (
            f"""{inst.address} {inst.funcname} {inst.bytelen} {inst.index}"""
        ).strip()


class SVCoverpoint(Formatter[Instruction]):
    @classmethod
    def fmt(
        cls,
        inst: Instruction,
        stats: Statistics,
        indent: int = 4,
        *args,
        **kwargs,
    ) -> str:
        func = inst.funcname
        blen = inst.bytelen
        addr = hex(inst.address).replace("0x", "'h", 1)
        fnlen = len(func)

        base = hex(stats.base_address).replace("0x", "'h", 1)
        maxlen = stats.max_funcname_len

        indent = max(1, indent)
        alignment = (1 + (maxlen + (indent - 1)) // indent * indent) - fnlen
        assignment = "=".rjust(alignment, " ")
        return (
            f"{indent * ' '}"
            f"bins {func} {assignment} {{ [ "
            f"(({addr} - {base}) >> 1) : "
            f"((({addr} - {base} + 'd{blen}) >> 1) - 1) "
            "] };"
        )
