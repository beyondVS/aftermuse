from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_minor_is_pinned() -> None:
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.14"


def test_example_environment_has_required_names() -> None:
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    required_names = {
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "ALADIN_TTB_KEY",
    }

    configured_names = {
        line.partition("=")[0]
        for line in content.splitlines()
        if line and not line.startswith("#")
    }

    assert required_names == configured_names


def test_compose_uses_postgresql_18_volume_layout() -> None:
    content = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "image: postgres:18.6-trixie" in content
    assert "postgres_data:/var/lib/postgresql" in content
    assert "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}" in content
