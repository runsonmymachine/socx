import typing as t
from pathlib import Path as Path

__all__ = ("ConverterValidator",)


class ConverterValidator:
    src: t.ClassVar[Path] = None
    target: t.ClassVar[Path] = None

    @classmethod
    def source_validator(cls, src: str | Path) -> bool:
        if not isinstance(src, Path):
            src = Path(src)
        cls.src = src
        return src.exists() and src.is_dir()

    @classmethod
    def target_validator(cls, target: str | Path) -> bool:
        if not isinstance(target, Path):
            target = Path(target)
        cls.target = target
        return target.exists() and target.is_dir()

    @classmethod
    def includes_validator(
        cls,
        src: Path,
        includes: list[str] | set[str] | tuple[str, ...],
        excludes: list[str] | set[str] | tuple[str, ...],
    ) -> bool:
        if not includes:
            return False
        if not isinstance(cls.src, Path):
            cls.src = Path(cls.src)
        if not isinstance(includes, list | set | tuple):
            return False
        paths = cls._extract_includes(cls.src, includes, excludes)
        return bool(paths) and all(path.is_file() for path in paths)

    @classmethod
    def _extract_includes(
        cls, src: Path, includes: set[Path], excludes: set[Path]
    ) -> set[Path]:
        paths = set()
        globpaths = set()
        for include in includes:
            if "*" not in include:
                paths.add(Path(cls.src / include))
            else:
                globpaths = globpaths.union(set(cls.src.glob(str(include))))
        for exclude in excludes:
            if "*" not in exclude:
                paths.discard(Path(cls.src / exclude))
            else:
                globpaths = globpaths.difference_update(
                    set(cls.src.glob(str(exclude)))
                )
        return paths.union(globpaths)
