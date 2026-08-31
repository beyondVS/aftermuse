import os
import subprocess
import sys

from django.conf import settings


def test_database_uses_postgresql() -> None:
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


def test_project_defaults_are_localized() -> None:
    assert settings.LANGUAGE_CODE == "ko-kr"
    assert settings.TIME_ZONE == "Asia/Seoul"
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


def test_invalid_debug_value_fails_at_startup() -> None:
    environment = os.environ.copy()
    environment["DJANGO_DEBUG"] = "sometimes"

    result = subprocess.run(
        [sys.executable, "src/manage.py", "check"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode != 0
    assert "DJANGO_DEBUG" in result.stderr
