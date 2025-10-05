from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        # Importa sinais para registro automático de auditoria (definidos mais tarde)
        from . import signals  # noqa: F401  # Import tardio
