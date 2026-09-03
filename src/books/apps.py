from django.apps import AppConfig


class BooksConfig(AppConfig):
    """도서 및 서지정보 도메인 설정이다."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "books"
