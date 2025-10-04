from __future__ import annotations

import re
from datetime import datetime

YEAR_RANGE_PATTERN = re.compile(r"^\s*(\d{4})\s*-\s*(\d{4})\s*$")


def get_default_year_range() -> tuple[int, int]:
    current_year = datetime.now().year
    return current_year - 1, current_year


def parse_year_range(raw_value: str | None) -> tuple[int, int]:
    if not raw_value:
        return get_default_year_range()
    match = YEAR_RANGE_PATTERN.match(raw_value)
    if not match:
        raise ValueError("年份范围格式应为YYYY-YYYY")
    start_year, end_year = map(int, match.groups())
    if start_year > end_year:
        raise ValueError("年份范围起始值不能大于结束值")
    return start_year, end_year


def clamp_max_num(raw_value: str | int | None, *, default: int, maximum: int) -> int:
    if raw_value in (None, ""):
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("最大数量必须是整数") from exc
    if value < 1:
        return 1
    if value > maximum:
        return maximum
    return value


def validate_keywords(keywords: str | None) -> str:
    cleaned = (keywords or "").strip()
    if not cleaned:
        raise ValueError("关键词不能为空")
    return cleaned
