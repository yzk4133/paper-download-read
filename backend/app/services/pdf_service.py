from __future__ import annotations

"""占位模块：负责 PDF 文本提取与清洗逻辑."""

import logging
import re
from pathlib import Path
from typing import Dict, Iterable, Iterator

from PyPDF2 import PdfReader  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

WHITESPACE_PATTERN = re.compile(r"\s+")


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Read a PDF file and return its textual content.

    The function leverages PyPDF2 to iterate over every page, concatenates the
    extracted text, and performs a light normalization to collapse consecutive
    whitespace. Any error will be raised to the caller so that higher level
    services can决定如何处理失败的文档。
    """

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:  # pragma: no cover - PyPDF specific failures
        raise RuntimeError(f"无法打开 PDF {pdf_path.name}: {exc}") from exc

    texts: list[str] = []
    for index, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - PyPDF specific failures
            raise RuntimeError(f"解析 PDF 第 {index + 1} 页失败: {exc}") from exc
        texts.append(page_text)

    joined = "\n".join(texts)
    normalized = WHITESPACE_PATTERN.sub(" ", joined)
    return normalized.strip()


def extract_batch(pdf_dir: Path) -> Iterator[Dict[str, str]]:
    """Iterate over all PDF files in a directory and yield their content.

    该函数主要用于批量解析任务：会按文件名排序依次处理每个 PDF，并在
    发生异常时记录日志但继续后续文件，确保单个文件的失败不会终止整体流程。
    """

    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF 目录不存在: {pdf_dir}")

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        try:
            yield {
                "file_name": pdf_path.name,
                "path": str(pdf_path),
                "text": extract_text_from_pdf(pdf_path),
            }
        except Exception as exc:  # pragma: no cover - expected to be rare
            logger.warning("解析 PDF %s 失败: %s", pdf_path.name, exc)
            yield {
                "file_name": pdf_path.name,
                "path": str(pdf_path),
                "text": "",
                "error": str(exc),
            }
