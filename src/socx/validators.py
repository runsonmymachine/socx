import typing as t
from pathlib import Path as Path

__all__ = ("PathValidator",)


class PathValidator:
    src: t.ClassVar[Path] = None
    target: t.ClassVar[Path] = None

    @classmethod
    def source_validator(cls, src: str | Path) -> bool:
        if not isinstance(src, Path):
            src = Path(src)
        return src.exists() and src.is_dir()

    @classmethod
    def target_validator(cls, target: str | Path) -> bool:
        if not isinstance(target, Path):
            target = Path(target)
        return target.is_dir() or not target.exists()

    @classmethod
    def includes_validator(
        cls,
        src: Path,
        includes: list[str] | set[str] | tuple[str, ...],
        excludes: list[str] | set[str] | tuple[str, ...],
    ) -> bool:
        if not includes:
            return False
        if not isinstance(src, Path):
            src = Path(src)
        if not isinstance(includes, list | set | tuple):
            return False
        paths = cls._extract_includes(src, includes, excludes)
        return bool(paths) and all(path.is_file() for path in paths)

    @classmethod
    def _extract_includes(
        cls, src: Path, includes: set[Path], excludes: set[Path]
    ) -> set[Path]:
        paths = set()
        globpaths = set()
        if not isinstance(src, Path):
            src = Path(src)
        for include in includes:
            if "*" not in include:
                paths.add(Path(src / include))
            else:
                globpaths = globpaths.union(set(src.glob(str(include))))
        for exclude in excludes:
            if "*" not in exclude:
                paths.discard(Path(src / exclude))
            else:
                globpaths.difference_update(set(src.glob(str(exclude))))
        return paths.union(globpaths)
