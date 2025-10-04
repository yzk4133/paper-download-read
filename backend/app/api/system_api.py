from __future__ import annotations

from pathlib import Path

from flask import current_app  # type: ignore[import-not-found]
from flask_restx import Namespace, Resource, fields  # type: ignore[import-not-found]

api = Namespace("system", description="系统信息接口")

storage_response = api.model(
    "StorageResponse",
    {
        "pdf_dir": fields.String(description="默认 PDF 保存目录"),
        "excel_dir": fields.String(description="默认 Excel 保存目录"),
        "log_dir": fields.String(description="日志目录"),
    },
)


@api.route("/storage")
class StorageResource(Resource):
    @api.marshal_with(storage_response)
    def get(self):
        config = current_app.config
        return {
            "pdf_dir": str(Path(config["PDF_DIR"])),
            "excel_dir": str(Path(config["EXCEL_DIR"])),
            "log_dir": str(Path(config["LOG_DIR"])),
        }
