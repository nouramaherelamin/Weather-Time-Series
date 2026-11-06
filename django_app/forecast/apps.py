from django.apps import AppConfig


class ForecastConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "forecast"

    def ready(self):
        # Load the trained model bundles ONCE when the server starts (not on every request).
        from django.conf import settings
        from . import ml
        ml.load_all(settings.MODELS_DIR)
