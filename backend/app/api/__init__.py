from __future__ import annotations

from flask import Blueprint, Flask  # type: ignore[import-not-found]
from flask_restx import Api  # type: ignore[import-not-found]

from .crawl_api import api as crawl_ns
from .parse_api import api as parse_ns
from .excel_api import api as excel_ns
from .system_api import api as system_ns


def register_namespaces(app: Flask) -> None:
    blueprint = Blueprint("api", __name__, url_prefix="/api")
    api = Api(
        blueprint,
        version="1.0",
        title="arXiv 文献解析 API",
        description="前后端分离的后端接口集合",
        doc="/docs",
    )

    api.add_namespace(crawl_ns)
    api.add_namespace(parse_ns)
    api.add_namespace(excel_ns)
    api.add_namespace(system_ns)

    app.register_blueprint(blueprint)
