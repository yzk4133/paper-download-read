from __future__ import annotations

import os
from typing import Type

from .base_config import BaseConfig
from .dev_config import DevelopmentConfig
from .prod_config import ProductionConfig


CONFIG_MAP: dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "dev": DevelopmentConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name: str | None = None) -> Type[BaseConfig]:
    """Resolve configuration class by name or environment variable."""
    config_key = (
        config_name
        or os.getenv("ARXIV_APP_CONFIG")
        or os.getenv("FLASK_ENV")
        or "default"
    ).lower()
    return CONFIG_MAP.get(config_key, DevelopmentConfig)
