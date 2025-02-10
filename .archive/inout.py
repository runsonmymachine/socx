from __future__ import annotations

import os as os
import sys as sys
import abc as abc
import typing as t
import dataclasses as dc
import argparse as argparse
from pathlib import Path as Path

from .constants import LST_FILE_SUFFIXES as LST_FILE_SUFFIXES
from .constants import DEFAULT_INPUT_PATH as DEFAULT_INPUT_PATH
from .constants import DEFAULT_OUTPUT_PATH as DEFAULT_OUTPUT_PATH

__all__ = ("FileInfo",)


@dc.dataclass(init=False)
class FileInfo:
    out_dir_path: str | Path
    in_dir_path: str | Path
    lst_file_paths: list[Path]

    def __init__(
        self, in_dir_path: str | Path, out_dir_path: str | Path
    ) -> None:
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
    def _correct_path(cls, path: str | Path, default: Path) -> Path:
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
        elif isinstance(paths, (list | tuple | set)):
            for path in paths:
                if path.suffix not in LST_FILE_SUFFIXES:
                    err = f"Invalid file path: {path}"
                    raise OSError(err)
        else:  # attempt to recover from user path or path-type mistake
            paths = Path(paths)
            if paths.is_dir():
                paths = cls._fetch_lists(paths)
            elif paths.is_file():
                paths = [paths]
            cls._validate_file_paths([paths])
