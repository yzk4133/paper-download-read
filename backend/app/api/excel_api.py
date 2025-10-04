from __future__ import annotations

from pathlib import Path

from flask import current_app, request, send_file  # type: ignore[import-not-found]
from flask_restx import Namespace, Resource, fields  # type: ignore[import-not-found]

from ..services.excel_service import generate_excel
from ..services.state_manager import (
    get_excel_state,
    get_parse_results,
    reset_excel_state,
    succeed_excel,
    fail_excel,
)

api = Namespace("excel", description="Excel 导出相关接口")

excel_generate_response = api.model(
    "ExcelGenerateResponse",
    {
        "success": fields.Boolean,
        "message": fields.String,
        "file": fields.String(description="生成的 Excel 文件名"),
        "path": fields.String(description="Excel 文件所在目录"),
    },
)

excel_status_response = api.model(
    "ExcelStatusResponse",
    {
        "status": fields.String,
        "message": fields.String,
        "file": fields.String,
        "path": fields.String,
        "updated_at": fields.String,
    },
)


@api.route("/generate")
class ExcelGenerate(Resource):
    @api.marshal_with(excel_generate_response)
    def post(self):
        payload = request.get_json(silent=True) or {}
        records = payload.get("records")
        if records is not None and not isinstance(records, list):
            api.abort(400, "records 字段必须为数组")

        output_dir = payload.get("output_dir")
        if not records:
            records = get_parse_results()

        if not records:
            fail_excel("暂无可用数据，请先完成解析任务。")
            return {
                "success": False,
                "message": "暂无可用数据，请先完成解析任务。",
                "file": None,
                "path": None,
            }, 400

        excel_dir = Path(output_dir).expanduser().resolve() if output_dir else Path(current_app.config["EXCEL_DIR"])
        reset_excel_state(target_dir=excel_dir)
        try:
            file_path = generate_excel(records, excel_dir)
        except Exception as exc:  # pragma: no cover - depends on pandas/openpyxl
            fail_excel(str(exc))
            return {
                "success": False,
                "message": str(exc),
                "file": None,
                "path": str(excel_dir),
            }, 500

        succeed_excel(file_path)
        return {
            "success": True,
            "message": "Excel 生成完成",
            "file": file_path.name,
            "path": str(file_path.parent),
        }


@api.route("/status")
class ExcelStatus(Resource):
    @api.marshal_with(excel_status_response)
    def get(self):
        state = get_excel_state()
        path_value = state.get("target_dir")
        if not path_value:
            file_path = state.get("file_path")
            if file_path:
                path_value = str(Path(file_path).parent)
        return {
            "status": state.get("status"),
            "message": state.get("message"),
            "file": Path(state.get("file_path") or "").name or None,
            "path": path_value,
            "updated_at": state.get("updated_at"),
        }


@api.route("/download")
class ExcelDownload(Resource):
    def get(self):
        state = get_excel_state()
        file_path = state.get("file_path")
        if not file_path or not Path(file_path).exists():
            api.abort(404, "Excel 文件尚未生成。")
        return send_file(file_path, as_attachment=True)
