"""Registro central de plugins configuráveis."""

from __future__ import annotations

import importlib
from functools import lru_cache

from django.conf import settings

PROVIDER_PATHS = {
    "exports": "plugins.exports.{name}.provider",
    "synthesis": "plugins.synthesis.{name}.provider",
    "hooks": "plugins.hooks.{name}.provider",
}


class PluginNotFound(Exception):
    pass


@lru_cache(maxsize=32)
def _load_provider(kind: str, name: str):
    module_path = PROVIDER_PATHS[kind].format(name=name)
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        raise PluginNotFound(f"Plugin {kind}:{name} não encontrado") from exc


def get_export_provider(name: str | None = None):
    fallback = getattr(settings, "DEFAULT_EXPORT_PLUGIN", "default")
    provider_name = name or fallback
    return _load_provider("exports", provider_name)


def get_synthesis_provider(name: str | None = None):
    fallback = getattr(settings, "DEFAULT_SYNTHESIS_PLUGIN", "default")
    provider_name = name or fallback
    return _load_provider("synthesis", provider_name)


def get_hook_provider(name: str | None = None):
    fallback = getattr(settings, "DEFAULT_HOOK_PLUGIN", "default")
    provider_name = name or fallback
    return _load_provider("hooks", provider_name)
