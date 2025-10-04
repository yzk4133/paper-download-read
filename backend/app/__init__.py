from flask import Flask
from flask_cors import CORS

from .config import get_config
from .utils.file_utils import ensure_runtime_directories
from .utils.log_utils import configure_logging
from .api import register_namespaces


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for the backend service."""
    app = Flask(__name__)

    config_class = get_config(config_name)
    app.config.from_object(config_class)

    configure_logging(app.config["LOG_DIR"], app.config.get("LOG_LEVEL", "INFO"))
    ensure_runtime_directories(
        pdf_dir=app.config["PDF_DIR"],
        excel_dir=app.config["EXCEL_DIR"],
        log_dir=app.config["LOG_DIR"],
    )

    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    register_namespaces(app)

    return app
