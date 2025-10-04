from __future__ import annotations

from pathlib import Path

from flask import current_app, request  # type: ignore[import-not-found]
from flask_restx import Namespace, Resource, fields  # type: ignore[import-not-found]

from ..services.parse_service import run_parse_job
from ..services.state_manager import get_parse_state

api = Namespace("parse", description="PDF 解析相关接口")

parse_request_model = api.model(
    "ParseRequest",
    {
        "records": fields.List(
            fields.Raw,
            required=False,
            description="可选：前端传入的论文元数据列表，用于对齐解析结果",
        ),
        "source": fields.String(required=False, description="自定义 PDF 目录路径"),
    },
)

parse_response_model = api.model(
    "ParseResponse",
    {
        "success": fields.Boolean,
        "message": fields.String,
        "status": fields.String,
        "summary": fields.Raw,
        "results": fields.List(fields.Raw),
    },
)

parse_progress_model = api.model(
    "ParseProgress",
    {
        "success": fields.Boolean,
        "status": fields.String,
        "message": fields.String,
        "current": fields.Integer,
        "total": fields.Integer,
        "last_error": fields.String,
        "updated_at": fields.String,
        "source_dir": fields.String,
    },
)


@api.route("/start")
class ParseStart(Resource):
    @api.expect(parse_request_model)
    @api.marshal_with(parse_response_model)
    def post(self):
        payload = request.get_json(silent=True) or {}
        source = payload.get("source")

        pdf_dir = Path(source) if source else Path(current_app.config["PDF_DIR"])
        records = payload.get("records")
        if records is not None and not isinstance(records, list):
            api.abort(400, "records 字段必须为数组")

        response = run_parse_job(pdf_dir=pdf_dir, records=records)
        status_code = 200 if response.get("success") else 500
        return response, status_code


@api.route("/progress")
class ParseProgress(Resource):
    @api.marshal_with(parse_progress_model)
    def get(self):
        state = get_parse_state()
        return {
            "success": state.get("status") in {"completed", "running"},
            "status": state.get("status"),
            "message": state.get("message"),
            "current": state.get("current", 0),
            "total": state.get("total", 0),
            "last_error": state.get("last_error"),
            "updated_at": state.get("updated_at"),
            "source_dir": state.get("source_dir"),
        }
