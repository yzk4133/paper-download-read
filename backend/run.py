from __future__ import annotations

import os

from app import create_app


if __name__ == "__main__":
    config_name = os.getenv("ARXIV_APP_CONFIG", "development")
    application = create_app(config_name)
    application.run(host="0.0.0.0", port=5000)
