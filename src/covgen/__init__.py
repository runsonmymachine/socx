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
import typing as t
import dataclasses as dc
import argparse as argparse
from pathlib import Path as Path


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


LST_SUFFIXES: t.Final[list[str]] = [".lst", ".list"]
"""Default list file suffixes."""

DEFAULT_INPUT_PATH = Path(
    Path(os.environ.get("WAREA", ""))
    / "PIXIE_ROM_FW"
    / "PixieROMApp"
    / "TapeOutRelease"
    / "PIXIE_E4"
    / "PxieParserOut"
).resolve()
"""Default output path for parser generated list files."""

DEFAULT_OUTPUT_PATH = Path(
    Path(__file__).parent.parent / "assets" / "converter_out"
).resolve()
"""Default output path for converter generated files."""


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------


T = t.TypeVar("T")

PathType = t.Union[str, Path, None]

# -----------------------------------------------------------------------------
# Dataclass Aliases
# -----------------------------------------------------------------------------


_DEFAULT_LIST = dc.field(default_factory=list, init=False)


_DEFAULT_STATISTICS = dc.field(
    default_factory=lambda: Statistics(), init=False
)


# -----------------------------------------------------------------------------
# Custom Classes
# -----------------------------------------------------------------------------


@dc.dataclass(init=False)
class FileInfo:
    out_dir_path: PathType
    in_dir_path: PathType
    lst_file_paths: list[Path]

    def __init__(self, in_dir_path: PathType, out_dir_path: PathType) -> None:
        self.in_dir_path = self._correct_path(in_dir_path, DEFAULT_INPUT_PATH)
        self.out_dir_path = self._correct_path(
            out_dir_path, DEFAULT_OUTPUT_PATH
        )
        self.lst_file_paths = self._fetch_lists(self.in_dir_path)
        self._validate(self.in_dir_path, self.lst_file_paths)

    @classmethod
    def _fetch_lists(cls, base_path: Path) -> list[Path]:
        lst = list(base_path.glob("*.lst"))
        lst.extend(list(base_path.glob("*.list")))
        return lst

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
    def _validate_base_path(cls, path: Path) -> t.Never:
        if not path.exists():
            err = f"Non existent path: {path}"
            raise OSError(err)

    @classmethod
    def _validate_file_paths(cls, paths: list[Path]) -> t.Never:
        if not bool(paths):
            err = f"No valid paths were found: {paths}."
            raise OSError(err)
        elif isinstance(paths, (list, tuple, set)):
            for path in paths:
                if path.suffix not in LST_SUFFIXES:
                    err = f"Invalid file path: {path}"
                    raise OSError(err)
        else:  # attempt to recover from user path or path-type mistake
            paths = Path(paths)
            if paths.is_dir():
                paths = cls._fetch_lists(paths)
            elif paths.is_file():
                paths = [paths]
            cls._validate_file_paths([paths])


class Formatter(abc.ABC, t.Generic[T]):
    """Format an object of type T to a user defined string format."""

    @classmethod
    @abc.abstractmethod
    def fmt(cls, obj: T, *args, **kwargs) -> str: ...


@dc.dataclass
class SVCoverpoint(Formatter["Instruction"]):
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


class LstLine(Formatter["Instruction"]):
    """
    Convert an instruction to its corresponding SystemVerilog covergroup
    representation string.
    """

    @classmethod
    def fmt(cls, inst: Instruction, *args, **kwargs) -> str:
        return (
            f"""{inst.address} {inst.funcname} {inst.bytelen} {inst.index}"""
        ).strip()


@dc.dataclass
class Statistics:
    """Collects statistics on consumed instructions."""

    base_address: int = -1
    """Base address, currently, address of the first parsed instruction."""
    max_funcname_len: int = -1
    """Maximum function name length of consumed instructions."""

    def consume(self, inst: Instruction) -> None:
        if inst is None:
            return
        if self.base_address == -1:
            self.base_address = inst.address
        if self.max_funcname_len < len(inst.funcname):
            self.max_funcname_len = len(inst.funcname)


@dc.dataclass
class ASM:
    """An ordered list of assembly instructions read from a file."""

    COMMENT_TOKENS: t.ClassVar[tuple[str, ...]] = ("#",)
    """Possible tokens for inline comments."""

    file: PathType
    """Assembly file name."""
    statistics: Statistics = _DEFAULT_STATISTICS
    """Statistics about the current instruction set."""
    instructions: list[Instruction] = _DEFAULT_LIST
    """Ordered list of assembly instructions parsed from consumed strings."""

    def consume(self, line: str) -> None:
        if self.is_comment(line):
            return
        instruction = Instruction.fromstr(line)
        self.statistics.consume(instruction)
        self.instructions.append(instruction)

    def to_sv(self, indent: int = 4) -> str:
        return "\n".join(
            SVCoverpoint.fmt(instruction, self.statistics, indent)
            for instruction in self.instructions
        )

    def to_lst(self) -> str:
        return "\n".join(
            LstLine.fmt(instruction) for instruction in self.instructions
        )

    def is_comment(self, line: str) -> bool:
        line = line.strip()
        return any(line.startswith(tok) for tok in ASM.COMMENT_TOKENS)

    def __post_init__(self) -> None:
        self.file = FileInfo._correct_path(self.file, None)


@dc.dataclass
class Instruction:
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
        args = line.strip().split()
        return cls(
            address=int(args[0], base=16),
            funcname=args[1].strip(),
            bytelen=int(args[2], base=10),
            index=int(args[3], base=10),
        )


# -----------------------------------------------------------------------------
# Main Logic
# -----------------------------------------------------------------------------


def prepare(info: FileInfo) -> None:
    info.out_dir_path.mkdir(exist_ok=True, parents=True)


def parse_one(file: Path) -> ASM:
    asm = ASM(file=file.name)
    lines = file.read_text().splitlines()
    for line in lines:
        asm.consume(line)
    return asm


def parse(info: FileInfo) -> list[ASM]:
    return [parse_one(file) for file in info.lst_file_paths]


def write(output_dir: Path, asm_modules: list[ASM]) -> None:
    for asm in asm_modules:
        output_file = output_dir / asm.file.with_suffix(".sv")
        output_file.write_text(asm.to_sv())
        print(f"SystemVerilog output successfuly written to {output_file}")


def _init_cli_parser() -> argparse.ArgumentParser:
    argparser = argparse.ArgumentParser(prog="lst_to_cov")
    argparser.add_argument(
        "-i",
        "--input",
        "--input-dir",
        dest="input_dir",
        nargs=1,
        type=Path,
        required=False,
        help=(
            "Path to parser output directory containing .lst files to be "
            "converted."
        ),
    )
    argparser.add_argument(
        "-o",
        "--output",
        "--output-dir",
        dest="output_dir",
        nargs=1,
        type=Path,
        help="Path to output directory for converter to dump output.",
        required=False,
    )
    argparser.add_argument(
        "-t",
        "--tab-width",
        dest="indent",
        nargs=1,
        type=int,
        default=4,
        required=False,
        action='store',
        help="Number of spaces to use for tab indentations."
    )
    return argparser


def _parse_cli_args(argparser: argparse.ArgumentParser) -> argparse.Namespace:
    return argparser.parse_args(sys.argv[1:])


def main() -> int:
    argparser = _init_cli_parser()
    args = _parse_cli_args(argparser)
    info = FileInfo(
        in_dir_path=args.input_dir[0] if bool(args.input_dir) else None,
        out_dir_path=args.output_dir[0] if bool(args.output_dir) else None,
    )
    prepare(info)
    write(info.out_dir_path, parse(info))


if __name__ == "__main__":
    main()
