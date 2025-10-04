from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

from .llm_service import analyze_paper
from .pdf_service import extract_text_from_pdf
from .state_manager import append_parse_result, begin_parse, complete_parse, fail_parse


SUCCESS_STATUSES = {"downloaded", "already_exists", "replaced_old_version"}
FIELD_LIMIT = 50


def _limit_fields(data: Mapping[str, object]) -> Dict[str, str]:
    limited: Dict[str, str] = {}
    for key in ("innovation", "method", "conclusion", "summary"):
        value = str(data.get(key, "") or "").strip()
        if len(value) > FIELD_LIMIT:
            limited[key] = value[: FIELD_LIMIT - 1].rstrip() + "…"
        else:
            limited[key] = value
    return limited


def _resolve_candidates(pdf_dir: Path, records: Iterable[Mapping[str, object]] | None) -> List[Dict[str, object]]:
    if records:
        candidates: List[Dict[str, object]] = []
        for record in records:
            if record.get("status") not in SUCCESS_STATUSES:
                continue
            file_name = record.get("file_name")
            if not file_name:
                continue
            candidate = dict(record)
            candidate["file_path"] = str(pdf_dir / str(file_name))
            candidates.append(candidate)
        return candidates

    # fallback to every PDF in directory
    candidates = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        candidates.append({
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "title": pdf_path.stem,
            "status": "existing",
        })
    return candidates


def _build_result(record: Mapping[str, object], extra: Mapping[str, object]) -> Dict[str, object]:
    data = dict(record)
    data.update(extra)
    data.setdefault("parsed_at", datetime.utcnow().isoformat(timespec="seconds"))
    return data


def run_parse_job(*, pdf_dir: Path, records: Iterable[Mapping[str, object]] | None = None) -> Dict[str, object]:
    candidates = _resolve_candidates(pdf_dir, records)
    total = len(candidates)
    if total == 0:
        fail_parse("没有可解析的 PDF。请先执行爬取任务。", source_dir=pdf_dir)
        return {
            "success": False,
            "message": "没有可解析的 PDF 文件。",
            "status": "failed",
            "summary": {"total": 0, "parsed": 0, "failed": 0},
            "results": [],
            "storage": {"pdf_dir": str(pdf_dir)},
        }

    begin_parse(total, source_dir=pdf_dir)
    parsed_results: List[Dict[str, object]] = []
    failed = 0

    for candidate in candidates:
        file_path = Path(candidate["file_path"])
        if not file_path.exists():
            failed += 1
            result = _build_result(
                candidate,
                {
                    "parse_status": "failed",
                    "parse_error": "文件不存在",
                    "innovation": "",
                    "method": "",
                    "conclusion": "",
                    "summary": "",
                },
            )
            append_parse_result(result)
            parsed_results.append(result)
            continue

        try:
            text = extract_text_from_pdf(file_path)
            llm_output = analyze_paper(text)
            limited_output = _limit_fields(llm_output)
            result = _build_result(
                candidate,
                {
                    **limited_output,
                    "parse_status": "succeeded",
                    "parse_error": "",
                },
            )
        except Exception as exc:  # pragma: no cover - depends on PyPDF2 behaviour
            failed += 1
            result = _build_result(
                candidate,
                {
                    "parse_status": "failed",
                    "parse_error": str(exc),
                    "innovation": "",
                    "method": "",
                    "conclusion": "",
                    "summary": "",
                },
            )
        append_parse_result(result)
        parsed_results.append(result)

    summary = {
        "total": total,
        "parsed": total - failed,
        "failed": failed,
    }

    if failed and failed == total:
        fail_parse("全部 PDF 解析失败，请检查日志。", source_dir=pdf_dir)
        success = False
        message = "解析失败，详见结果。"
        status = "failed"
    else:
        complete_parse()
        success = True
        message = "解析完成。"
        status = "completed"

    return {
        "success": success,
        "message": message,
        "status": status,
        "summary": summary,
        "results": parsed_results,
        "storage": {"pdf_dir": str(pdf_dir)},
    }
