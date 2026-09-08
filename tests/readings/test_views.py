from datetime import date, timedelta

import pytest
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse

from books.models import Book
from readings.models import Reading
from readings.services import ActiveReadingExistsError
from reflections.models import Interview


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


def test_completed_reading_cta_uses_start_boundary_without_side_effect(
    client, user, book
) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    client.force_login(user)

    content = client.get(reverse("readings:detail", args=[reading.pk])).content.decode()

    assert reverse("reflections:interview_start", args=[reading.pk]) in content
    assert Interview.objects.filter(reading=reading).count() == 0


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


def test_htmx_state_success_and_form_error_expose_swap_and_focus_contract(
    client, user, book
) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    client.force_login(user)
    url = reverse("readings:change_state", args=[reading.pk])

    invalid_response = client.post(
        url,
        {"status": Reading.Status.COMPLETED, "completed_on": ""},
        HTTP_HX_REQUEST="true",
    )
    success_response = client.post(
        url,
        {"status": Reading.Status.COMPLETED, "completed_on": date.today()},
        HTTP_HX_REQUEST="true",
    )

    invalid_content = invalid_response.content.decode()
    success_content = success_response.content.decode()
    assert invalid_response.status_code == 400
    assert invalid_response.headers["HX-Retarget"] == "#reading-panel"
    assert invalid_response.headers["HX-Reswap"] == "outerHTML"
    assert invalid_response.headers["HX-Trigger-After-Settle"] == "readingPanelSettled"
    assert 'id="reading-panel"' in invalid_content
    assert "완독 상태에는 완독일이 필요합니다." in invalid_content
    assert "data-reading-result" in invalid_content
    assert "autofocus" in invalid_content
    assert success_response.status_code == 200
    assert success_response.headers["HX-Trigger-After-Settle"] == "readingPanelSettled"
    assert "독서 상태를 저장했습니다." in success_content
    assert 'tabindex="-1"' in success_content
    assert "data-reading-result" in success_content
    assert "autofocus" in success_content


def test_htmx_and_full_form_errors_preserve_the_same_invalid_input(
    client, user, book
) -> None:
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )
    client.force_login(user)
    future_date = (date.today() + timedelta(days=1)).isoformat()
    url = reverse("readings:change_state", args=[reading.pk])
    payload = {"status": Reading.Status.COMPLETED, "completed_on": future_date}

    full_response = client.post(url, payload)
    htmx_response = client.post(url, payload, HTTP_HX_REQUEST="true")

    for response in (full_response, htmx_response):
        content = response.content.decode()
        assert response.status_code == 400
        assert "완독일은 오늘 이후로 지정할 수 없습니다." in content
        assert f'value="{future_date}"' in content
        assert "현재 상태: 읽는 중" in content
    assert "<!doctype html>" in full_response.content.decode()
    assert "<!doctype html>" not in htmx_response.content.decode()
    assert htmx_response.headers["HX-Retarget"] == "#reading-panel"
    assert htmx_response.headers["HX-Reswap"] == "outerHTML"


def test_htmx_database_error_swaps_retryable_panel_and_preserves_state(
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
        HTTP_HX_REQUEST="true",
    )

    reading.refresh_from_db()
    assert response.status_code == 400
    assert response.headers["HX-Retarget"] == "#reading-panel"
    assert response.headers["HX-Reswap"] == "outerHTML"
    assert "잠시 후 다시 시도해 주세요." in response.content.decode()
    assert reading.status == Reading.Status.READING
    assert reading.completed_on is None


@pytest.mark.parametrize("is_htmx", [False, True])
def test_active_reading_conflict_links_to_owned_reading_and_preserves_values(
    client, user, book, is_htmx
) -> None:
    completed = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    active = Reading.objects.create(user=user, book=book, status=Reading.Status.READING)
    client.force_login(user)
    headers = {"HTTP_HX_REQUEST": "true"} if is_htmx else {}

    response = client.post(
        reverse("readings:change_state", args=[completed.pk]),
        {"status": Reading.Status.WANT_TO_READ, "completed_on": ""},
        **headers,
    )

    completed.refresh_from_db()
    content = response.content.decode()
    assert response.status_code == 400
    assert "진행 중인 다른 Reading이 있어 상태를 바꿀 수 없습니다." in content
    assert reverse("readings:detail", args=[active.pk]) in content
    assert "진행 중인 Reading 보기" in content
    assert completed.status == Reading.Status.COMPLETED
    assert completed.completed_on == date.today()
    if is_htmx:
        assert response.headers["HX-Retarget"] == "#reading-panel"
        assert response.headers["HX-Reswap"] == "outerHTML"


def test_conflict_response_never_links_to_another_users_reading(
    client, user, book, django_user_model, monkeypatch
) -> None:
    completed = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    other_user = django_user_model.objects.create_user(
        username="conflict-other-owner", password="strong-reader-password-123"
    )
    other_reading = Reading.objects.create(
        user=other_user, book=book, status=Reading.Status.READING
    )
    client.force_login(user)

    def raise_cross_owner_conflict(**kwargs) -> None:
        raise ActiveReadingExistsError(other_reading)

    monkeypatch.setattr(
        "readings.views.change_reading_state", raise_cross_owner_conflict
    )
    response = client.post(
        reverse("readings:change_state", args=[completed.pk]),
        {"status": Reading.Status.WANT_TO_READ, "completed_on": ""},
    )

    content = response.content.decode()
    assert response.status_code == 400
    assert reverse("readings:detail", args=[other_reading.pk]) not in content
    assert "진행 중인 Reading 보기" not in content
