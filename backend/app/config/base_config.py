from __future__ import annotations

from pathlib import Path


class BaseConfig:
    """Base configuration shared across environments."""

    BASE_DIR = Path(__file__).resolve().parents[2]
    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    USER_AGENT = "ArXivMiniDownloader/2.0"

    PDF_DIR = BASE_DIR / "pdf_files"
    EXCEL_DIR = BASE_DIR / "excel_output"
    LOG_DIR = BASE_DIR / "logs"

    DEFAULT_MAX_NUM = 5
    MAX_ALLOWED_NUM = 10
    PRE_FETCH_CAP = 100
    RATE_LIMIT_SECONDS = 1.0
    JITTER_RANGE = (0.1, 0.3)
    MAX_RETRIES = 3
    RETRY_BACKOFF = (0.5, 1.0, 2.0)
    API_TIMEOUT = (10, 30)
    MIN_PDF_SIZE_BYTES = 10 * 1024
    MAX_FILENAME_LENGTH = 120

    RESTX_MASK_SWAGGER = False
    ERROR_404_HELP = False

    CORS_ORIGINS = "*"
    LOG_LEVEL = "INFO"


__all__ = ["BaseConfig"]
