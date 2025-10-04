from __future__ import annotations

from pathlib import Path
from typing import Iterable


def ensure_runtime_directories(*, pdf_dir: Path, excel_dir: Path, log_dir: Path) -> None:
    for directory in filter(None, (pdf_dir, excel_dir, log_dir)):
        directory.mkdir(parents=True, exist_ok=True)


def resolve_directory(base: Path, *parts: Iterable[str]) -> Path:
    path = base.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path
