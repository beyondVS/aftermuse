from datetime import date

import pytest
from django.db import DatabaseError
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


@pytest.mark.parametrize(
    ("status", "completed_on", "expects_completed_content"),
    [
        (Reading.Status.WANT_TO_READ, None, False),
        (Reading.Status.READING, None, False),
        (Reading.Status.COMPLETED, date.today(), True),
    ],
)
def test_detail_renders_status_specific_actions_and_book_metadata(
    client, user, book, status, completed_on, expects_completed_content
) -> None:
    book.authors = "저자"
    book.publisher = "출판사"
    book.cover_url = "https://images.example.test/cover.jpg"
    book.save()
    reading = Reading.objects.create(
        user=user, book=book, status=status, completed_on=completed_on
    )
    client.force_login(user)

    response = client.get(reverse("readings:detail", args=[reading.pk]))
    content = response.content.decode()

    assert f"현재 상태: {reading.get_status_display()}" in content
    assert 'src="https://images.example.test/cover.jpg"' in content
    assert 'alt="View 테스트 표지"' in content
    assert ("AI 독서노트 만들기" in content) is expects_completed_content
    assert ("새 Reading 시작" in content) is expects_completed_content


def test_detail_uses_title_when_optional_book_metadata_is_missing(
    client, user, book
) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    client.force_login(user)

    content = client.get(reverse("readings:detail", args=[reading.pk])).content.decode()

    assert "View 테스트" in content
    assert "표지" not in content
    assert "저자 ·" not in content
    assert "출판사 ·" not in content


def test_detail_exposes_accessible_htmx_loading_state(client, user, book) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    client.force_login(user)

    content = client.get(reverse("readings:detail", args=[reading.pk])).content.decode()

    assert 'id="reading-loading"' in content
    assert 'role="status"' in content
    assert 'aria-busy="false"' in content
    assert 'hx-indicator="#reading-loading"' in content


def test_change_state_returns_full_error_and_preserves_state_after_database_failure(
    client, user, book, monkeypatch
) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    client.force_login(user)
    monkeypatch.setattr(
        "readings.views.change_reading_state",
        lambda **kwargs: (_ for _ in ()).throw(DatabaseError()),
    )

    response = client.post(
        reverse("readings:change_state", args=[reading.pk]),
        {"status": Reading.Status.COMPLETED, "completed_on": date.today()},
    )

    reading.refresh_from_db()
    assert response.status_code == 400
    assert "잠시 후 다시 시도해 주세요." in response.content.decode()
    assert reading.status == Reading.Status.READING
    assert reading.completed_on is None


def test_change_state_post_is_owner_only(client, user, book, django_user_model) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    other_user = django_user_model.objects.create_user(
        username="state-other-owner", password="strong-reader-password-123"
    )
    client.force_login(other_user)

    response = client.post(
        reverse("readings:change_state", args=[reading.pk]),
        {"status": Reading.Status.COMPLETED, "completed_on": date.today()},
    )

    assert response.status_code == 404


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
