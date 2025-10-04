from __future__ import annotations

from .base_config import BaseConfig


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    LOG_LEVEL = "DEBUG"


__all__ = ["DevelopmentConfig"]
