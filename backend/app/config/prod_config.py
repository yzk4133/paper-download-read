from __future__ import annotations

from .base_config import BaseConfig


class ProductionConfig(BaseConfig):
    DEBUG = False
    LOG_LEVEL = "INFO"


__all__ = ["ProductionConfig"]
