import os
import shutil
import subprocess
import sys

from django.conf import settings

ENVIRONMENT_NAMES = (
    "DJANGO_SECRET_KEY",
    "DJANGO_DEBUG",
    "DJANGO_ALLOWED_HOSTS",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
)


def test_database_uses_postgresql() -> None:
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


def test_project_defaults_are_localized() -> None:
    assert settings.LANGUAGE_CODE == "ko-kr"
    assert settings.TIME_ZONE == "Asia/Seoul"
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


def test_environment_values_use_declared_types() -> None:
    assert isinstance(settings.DEBUG, bool)
    assert isinstance(settings.ALLOWED_HOSTS, list)
    assert isinstance(settings.DATABASES["default"]["PORT"], int)


def test_project_root_dotenv_is_loaded_without_cli_injection(tmp_path) -> None:
    project_root = tmp_path / "project"
    project_source = project_root / "src"
    shutil.copytree("src/config", project_source / "config")
    shutil.copytree("src/accounts", project_source / "accounts")
    shutil.copytree("src/books", project_source / "books")
    shutil.copy2("src/manage.py", project_source / "manage.py")
    (project_source / "static").mkdir()
    (project_root / ".env").write_text(
        "\n".join(
            (
                "DJANGO_SECRET_KEY=test-secret-key",
                "DJANGO_DEBUG=false",
                "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1",
                "POSTGRES_DB=aftermuse",
                "POSTGRES_USER=aftermuse",
                "POSTGRES_PASSWORD=aftermuse",
                "POSTGRES_HOST=127.0.0.1",
                "POSTGRES_PORT=5432",
            )
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    for name in ENVIRONMENT_NAMES:
        environment.pop(name, None)

    result = subprocess.run(
        [sys.executable, "src/manage.py", "check"],
        capture_output=True,
        check=False,
        cwd=project_root,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_os_environment_takes_priority_over_project_dotenv(tmp_path) -> None:
    project_root = tmp_path / "project"
    project_source = project_root / "src"
    shutil.copytree("src/config", project_source / "config")
    shutil.copytree("src/accounts", project_source / "accounts")
    shutil.copytree("src/books", project_source / "books")
    shutil.copy2("src/manage.py", project_source / "manage.py")
    (project_source / "static").mkdir()
    (project_root / ".env").write_text(
        "\n".join(
            (
                "DJANGO_SECRET_KEY=dotenv-secret-key",
                "DJANGO_DEBUG=false",
                "DJANGO_ALLOWED_HOSTS=localhost",
                "POSTGRES_DB=aftermuse",
                "POSTGRES_USER=aftermuse",
                "POSTGRES_PASSWORD=aftermuse",
                "POSTGRES_HOST=127.0.0.1",
                "POSTGRES_PORT=5432",
            )
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    for name in ENVIRONMENT_NAMES:
        environment.pop(name, None)
    environment["DJANGO_DEBUG"] = "true"

    result = subprocess.run(
        [
            sys.executable,
            "src/manage.py",
            "shell",
            "-c",
            "from django.conf import settings; print(settings.DEBUG)",
        ],
        capture_output=True,
        check=False,
        cwd=project_root,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.rstrip().endswith("True")
