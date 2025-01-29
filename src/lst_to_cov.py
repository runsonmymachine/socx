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
import typing as t
import argparse as argparse
from pathlib import Path as Path
import dataclasses as dc


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


LST_SUFFIXES: t.Final[list[str]] = [".lst", ".list"]
"""Default list file suffixes."""

PARSER_OUTPUT_PATH = Path(
    Path(os.environ.get("WAREA", ""))
    / "PIXIE_ROM_FW"
    / "PixieROMApp"
    / "TapeOutRelease"
    / "PIXIE_E4"
    / "PxieParserOut"
).resolve()
"""Default output path for parser generated list files."""

CONVERTER_OUTPUT_PATH = Path(
    Path(__file__).parent / "tests" / "assets" / "lst_to_cov" / "sv_out"
).resolve()
"""Default output path for converter generated SystemVerilog files."""


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------


PathType = t.Union[str, Path, None]


# -----------------------------------------------------------------------------
# Custom Classes
# -----------------------------------------------------------------------------


class ASMBase:
    """Base ASM class."""


@dc.dataclass(repr=False)
class ASM:
    """An ordered list of assembly instructions read from a file."""

    COMMENT_TOKENS: t.ClassVar[tuple[str, ...]] = ("#",)
    """Possible tokens for inline comments."""
    base: int
    """Base address, i.e. address of first instruction."""
    filename: str
    """Assembly file name."""
    instructions: list[Instruction]
    """Ordered list of assembly instructions."""

    def __init__(self, filename: str) -> None:
        self.base = None
        self.filename = filename
        self.instructions = []

    def to_sv(self) -> str:
        return "\n".join(
            instruction.to_sv() for instruction in self.instructions
        )

    def to_lst(self) -> str:
        return "\n".join(
            instruction.to_lst() for instruction in self.instructions
        )

    def consume(self, line: str) -> None:
        if self.is_comment(line):
            return
        inst = Instruction.fromstr(line)
        if self.base is None:
            self.base = inst.address
        inst.base = self.base
        self.instructions.append(inst)

    def is_comment(self, line: str) -> bool:
        line = line.strip()
        return any(line.startswith(tok) for tok in ASM.COMMENT_TOKENS)

    def __str__(self) -> str:
        return "\n".join(str(instruction) for instruction in self.instructions)

    def __repr__(self) -> str:
        return "\n".join(
            repr(instruction) for instruction in self.instructions
        )


class InstructionBase:
    """Instruction base mixin class."""

    base: int

    def __init__(self, *args, **kwargs):
        self.base = None


@dc.dataclass
class Instruction(InstructionBase):
    """Represents a single instruction in the list file."""

    address: int
    """Address."""
    funcname: str
    """Function name."""
    bytelen: int
    """Length in bytes (decimal)."""
    index: int
    """Index (4bytes lines, decimal)."""

    @classmethod
    def fromstr(cls, line: str) -> t.Self:
        """
        Create an Instruction instance from an instruction line read from a
        list file.
        """
        args = [field.strip() for field in line.split()]
        addr, fn, blen, idx = (
            int(args[0], 16),
            args[1],
            int(args[2]),
            int(args[3]),
        )
        return cls(addr, fn, blen, idx)

    def to_sv(self) -> str:
        return self.__sv_repr__()

    def to_lst(self) -> str:
        return self.__lst_repr__()

    def __repr__(self) -> str:
        return self.__sv_repr__()

    def __sv_repr__(self) -> str:
        """
        Convert an instruction to its corresponding SystemVerilog covergroup
        representation string.
        """
        return f"""
        bins {self.funcname} = {{[
            (('h{self.address} - 'h{self.base}) >> 1) :
            (('h{self.address} - 'h{self.base} + {self.bytelen}) >> 1) - 1
        ]}};
        """.strip()

    def __lst_repr__(self) -> str:
        """
        Convert an instruction to its corresponding SystemVerilog covergroup
        representation string.
        """
        return f"""
        {self.address} {self.funcname} {self.bytelen} {self.index}
        """.strip()


@dc.dataclass(init=False)
class FileInfo:
    out_base_path: PathType
    lst_base_path: PathType
    lst_file_paths: list[Path]

    def __init__(self, lst_base: PathType, out_base: PathType) -> None:
        self.lst_file_paths = self._fetch_lists(lst_base)
        self.lst_base_path = self._correct_path(lst_base, PARSER_OUTPUT_PATH)
        self.out_base_path = self._correct_path(
            out_base, CONVERTER_OUTPUT_PATH
        )
        self._validate(self.lst_base_path, self.lst_file_paths)

    @classmethod
    def _correct_path(cls, path: PathType, default: Path) -> Path:
        if path is None:
            return default
        elif isinstance(path, str):
            return Path(path)
        else:
            return path

    @classmethod
    def _validate(cls, base, lst) -> t.Never:
        cls._validate_base_path(base)
        cls._validate_file_paths(lst)

    @classmethod
    def _fetch_lists(cls, base_path: Path) -> list[Path]:
        lst = list(base_path.glob("*.lst"))
        lst.extend(list(base_path.glob("*.list")))
        return lst

    @classmethod
    def _validate_base_path(cls, path: t.Union[Path]) -> t.Never:
        assert path.exists()
        assert path.is_dir()

    @classmethod
    def _validate_file_paths(cls, paths: list[Path]) -> t.Never:
        if not bool(paths):
            err = f"No valid paths were found: {paths=}."
            raise OSError(err)
        for path in paths:
            assert path.is_file()
            assert path.suffix in LST_SUFFIXES


# -----------------------------------------------------------------------------
# Main Logic
# -----------------------------------------------------------------------------


def prepare(info: FileInfo) -> None:
    info.out_base_path.mkdir(exist_ok=True, parents=True)


def parse_one(file: Path) -> ASM:
    asm = ASM()
    text = file.read_text()
    lines = text.splitlines()
    for line in lines:
        asm.consume(line)
    return asm


def parse(info: FileInfo) -> dict[str, ASM]:
    filename_to_asm = {}
    for file in info.lst_file_paths:
        filename_to_asm[file.name] = parse_one(file)
    return filename_to_asm


def write(info: FileInfo, filename_to_asm: dict[str, ASM]) -> None:
    for filename, asm in filename_to_asm.items():
        lst_filepath = info.out_base_path / filename
        sv_filepath = lst_filepath.with_suffix(".sv")
        sv_filepath.write_text(asm.to_sv())
        print(f"SystemVerilog output successfuly written to {sv_filepath}")


def main() -> int:
    argparser = argparse.ArgumentParser(prog="lst_to_cov")
    argparser.add_argument(
        "-i",
        "--path-in",
        dest="path_in",
        nargs=1,
        type=Path,
        help="Path to parser output directory containing .lst files to be converted.",
        required=False,
    )
    argparser.add_argument(
        "-o",
        "--path-out",
        dest="path_out",
        nargs=1,
        type=Path,
        help="Path to output directory for converter to dump output.",
        required=False,
    )
    args = argparser.parse_args(sys.argv[1:])
    in_base_path = args.path_in[0] if bool(args.path_in) else None
    out_base_path = args.path_out[0] if bool(args.path_out) else None
    info = FileInfo(in_base_path, out_base_path)
    prepare(info)
    write(info, parse(info))


if __name__ == "__main__":
    main()
