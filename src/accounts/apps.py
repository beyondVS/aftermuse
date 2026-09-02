from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """사용자 계정과 인증 도메인 설정이다."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
