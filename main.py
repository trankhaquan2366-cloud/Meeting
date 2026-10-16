"""Compatibility entry point for ASGI servers configured with ``main:app``."""

from app.main import app

__all__ = ["app"]
