"""Run the API with uvicorn: ``python -m src.main``."""

from __future__ import annotations

import uvicorn

from src.core.config import get_settings


def main() -> None:
    """Start the uvicorn server using application settings."""
    settings = get_settings()
    uvicorn.run(
        "src.main.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,
    )


if __name__ == "__main__":
    main()
