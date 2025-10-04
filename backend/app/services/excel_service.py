from __future__ import annotations

"""占位模块：负责生成 Excel 报告逻辑."""

from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd  # type: ignore[import-not-found]


DEFAULT_COLUMNS: Sequence[str] = (
    "title",
    "arxiv_id",
    "id_with_version",
    "file_name",
    "status",
    "innovation",
    "method",
    "conclusion",
    "summary",
    "parse_status",
    "parse_error",
    "parsed_at",
)


def _ensure_dataframe(records: Iterable[Mapping[str, object]]) -> pd.DataFrame:
    data = [dict(record) for record in records]
    if not data:
        raise ValueError("没有可导出的记录，请先完成解析任务。")

    df = pd.DataFrame(data)
    for column in DEFAULT_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    return df[list(DEFAULT_COLUMNS)]


def generate_excel(records: Iterable[Mapping[str, object]], destination: Path) -> Path:
    """Generate an Excel report from parsed records.

    :param records: Iterable of dictionaries containing parsed paper metadata.
    :param destination: Directory where the Excel file should be saved.
    :returns: The path to the generated Excel file.
    """

    destination.mkdir(parents=True, exist_ok=True)
    dataframe = _ensure_dataframe(records)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_path = destination / f"arxiv_summary_{timestamp}.xlsx"

    dataframe.to_excel(file_path, index=False)
    return file_path
