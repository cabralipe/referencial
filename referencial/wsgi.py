"""WSGI entry point that proxies to the actual project module."""
from config.wsgi import application

__all__ = ["application"]
