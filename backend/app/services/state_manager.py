from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


_parse_state: Dict[str, object] = {
    "status": "idle",
    "total": 0,
    "current": 0,
    "message": "等待解析任务",
    "last_error": None,
    "results": [],
    "started_at": None,
    "finished_at": None,
    "updated_at": None,
    "source_dir": None,
}

_excel_state: Dict[str, object] = {
    "status": "idle",
    "file_path": None,
    "message": "Excel 尚未生成",
    "updated_at": None,
    "target_dir": None,
}

_LOCK = Lock()


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def begin_parse(total: int, message: Optional[str] = None, source_dir: Optional[Path] = None) -> None:
    with _LOCK:
        _parse_state.update(
            {
                "status": "running",
                "total": int(total),
                "current": 0,
                "message": message or "解析任务已启动",
                "last_error": None,
                "results": [],
                "started_at": _now_iso(),
                "finished_at": None,
                "updated_at": _now_iso(),
                "source_dir": str(source_dir) if source_dir else _parse_state.get("source_dir"),
            }
        )


def append_parse_result(record: Dict[str, object]) -> None:
    with _LOCK:
        results: List[Dict[str, object]] = _parse_state.setdefault("results", [])  # type: ignore[assignment]
        results.append(record)
        _parse_state["current"] = min(_parse_state.get("current", 0) + 1, _parse_state.get("total", 0))
        _parse_state["updated_at"] = _now_iso()


def complete_parse(message: Optional[str] = None) -> None:
    with _LOCK:
        _parse_state["status"] = "completed"
        _parse_state["message"] = message or "解析任务完成"
        _parse_state["finished_at"] = _now_iso()
        _parse_state["current"] = _parse_state.get("total", 0)
        _parse_state["updated_at"] = _now_iso()


def fail_parse(error_message: str, *, source_dir: Optional[Path] = None) -> None:
    with _LOCK:
        _parse_state["status"] = "failed"
        _parse_state["message"] = "解析任务失败"
        _parse_state["last_error"] = error_message
        _parse_state["results"] = []
        _parse_state["finished_at"] = _now_iso()
        _parse_state["updated_at"] = _now_iso()
        if source_dir is not None:
            _parse_state["source_dir"] = str(source_dir)


def get_parse_state() -> Dict[str, object]:
    with _LOCK:
        state = deepcopy(_parse_state)
        results = state.get("results")
        if isinstance(results, list):
            # Return a shallow copy to avoid accidental mutation
            state["results"] = list(results)
        return state


def get_parse_results() -> List[Dict[str, object]]:
    state = get_parse_state()
    results = state.get("results", [])
    if isinstance(results, list):
        return list(results)
    return []


def reset_excel_state(*, target_dir: Optional[Path] = None) -> None:
    with _LOCK:
        _excel_state.update(
            {
                "status": "running",
                "file_path": None,
                "message": "正在生成 Excel 报告",
                "updated_at": _now_iso(),
                "target_dir": str(target_dir) if target_dir else _excel_state.get("target_dir"),
            }
        )


def succeed_excel(file_path: Path) -> None:
    with _LOCK:
        _excel_state["status"] = "completed"
        _excel_state["file_path"] = str(file_path)
        _excel_state["message"] = "Excel 生成完成"
        _excel_state["updated_at"] = _now_iso()
        _excel_state["target_dir"] = str(file_path.parent)


def fail_excel(error_message: str) -> None:
    with _LOCK:
        _excel_state["status"] = "failed"
        _excel_state["message"] = error_message
        _excel_state["updated_at"] = _now_iso()


def get_excel_state() -> Dict[str, object]:
    with _LOCK:
        return deepcopy(_excel_state)
