from django.apps import AppConfig


class CadresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cadres"

    def ready(self):
        from . import signals  # noqa: F401
