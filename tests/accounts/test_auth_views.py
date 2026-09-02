import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

PASSWORD = "strong-reader-password-123"


@pytest.mark.django_db
def test_signup_creates_user_logs_them_in_and_redirects_home(client) -> None:
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "new-reader",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )

    user_model = get_user_model()
    user = user_model.objects.get(username="new-reader")

    assert response.status_code == 302
    assert response.url == reverse(settings.LOGIN_REDIRECT_URL)
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_signup_shows_a_username_error_when_username_is_taken(client) -> None:
    get_user_model().objects.create_user(username="existing-reader", password=PASSWORD)

    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "existing-reader",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors["username"]
    assert response.context["form"].errors["username"][0] in response.content.decode()


@pytest.mark.django_db
def test_login_redirects_valid_credentials_to_home(client) -> None:
    get_user_model().objects.create_user(username="reader", password=PASSWORD)

    response = client.post(
        reverse("accounts:login"),
        {"username": "reader", "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == reverse(settings.LOGIN_REDIRECT_URL)


@pytest.mark.django_db
def test_logout_post_clears_session_and_redirects_home(client) -> None:
    user = get_user_model().objects.create_user(username="reader", password=PASSWORD)
    client.force_login(user)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == 302
    assert response.url == reverse("home")
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_logout_get_is_not_allowed(client) -> None:
    response = client.get(reverse("accounts:logout"))

    assert response.status_code == 405


@pytest.mark.django_db
def test_logout_rejects_missing_csrf_token_and_accepts_page_token() -> None:
    user = get_user_model().objects.create_user(username="reader", password=PASSWORD)
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    rejected_response = client.post(reverse("accounts:logout"))
    page_response = client.get(reverse("home"))
    csrf_token = page_response.cookies["csrftoken"].value
    accepted_response = client.post(
        reverse("accounts:logout"),
        {"csrfmiddlewaretoken": csrf_token},
    )

    assert rejected_response.status_code == 403
    assert accepted_response.status_code == 302
    assert accepted_response.url == reverse("home")
