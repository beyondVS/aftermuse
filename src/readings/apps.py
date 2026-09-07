from django.apps import AppConfig


class ReadingsConfig(AppConfig):
    """Reading 도메인 앱 설정을 제공한다."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "readings"
