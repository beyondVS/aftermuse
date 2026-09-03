import pytest
from django.conf import settings
from django.contrib.auth import get_user_model


def test_project_uses_accounts_user_model() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model()._meta.label == "accounts.User"


@pytest.mark.django_db
def test_user_password_is_hashed() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="reader",
        password="safe-reading-password",
    )
    assert user.password != "safe-reading-password"
    assert user.check_password("safe-reading-password")
