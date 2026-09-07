from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from books.models import Book
from readings.models import Reading


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="view-owner", password="strong-reader-password-123"
    )


@pytest.fixture
def book(db) -> Book:
    return Book.objects.create(isbn13="9788937834792", title="View 테스트")


def test_book_entry_requires_login_and_explicit_creation(client, user, book) -> None:
    entry_url = reverse("readings:book_entry", args=[book.pk])
    assert client.get(entry_url).status_code == 302
    client.force_login(user)
    response = client.get(entry_url)
    created = client.post(
        reverse("readings:create", args=[book.pk]), {"status": Reading.Status.READING}
    )

    assert response.status_code == 200
    assert "어떤 상태로 시작할까요?" in response.content.decode()
    assert created.status_code == 302
    assert Reading.objects.filter(user=user, book=book).count() == 1


def test_detail_is_owner_only_and_htmx_state_response(
    client, user, book, django_user_model
) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    other_user = django_user_model.objects.create_user(
        username="other-owner", password="strong-reader-password-123"
    )
    client.force_login(other_user)
    assert client.get(reverse("readings:detail", args=[reading.pk])).status_code == 404
    client.force_login(user)
    response = client.post(
        reverse("readings:change_state", args=[reading.pk]),
        {"status": Reading.Status.COMPLETED, "completed_on": date.today()},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert 'id="reading-panel"' in response.content.decode()
    assert "현재 상태: 완독" in response.content.decode()


def test_change_state_rejects_missing_csrf_token(user, book) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    response = client.post(
        reverse("readings:change_state", args=[reading.pk]),
        {"status": Reading.Status.COMPLETED, "completed_on": date.today()},
    )

    assert response.status_code == 403
