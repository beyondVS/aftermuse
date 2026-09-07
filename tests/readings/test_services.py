from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections

from books.models import Book
from readings.models import Reading
from readings.services import (
    ActiveReadingExistsError,
    ReadingHistoryExistsError,
    ReadingLockedError,
    change_reading_state,
    create_initial_reading,
    create_rereading,
    update_completion_date,
)


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="service-owner", password="strong-reader-password-123"
    )


@pytest.fixture
def book(db) -> Book:
    return Book.objects.create(isbn13="9788937834791", title="Service 테스트")


def test_initial_creation_reuses_active_and_requires_explicit_rereading(
    user, book
) -> None:
    result = create_initial_reading(
        user=user, book=book, status=Reading.Status.READING, completed_on=None
    )
    repeated = create_initial_reading(
        user=user, book=book, status=Reading.Status.WANT_TO_READ, completed_on=None
    )
    result.reading.status = Reading.Status.COMPLETED
    result.reading.completed_on = date.today()
    result.reading.save()

    assert result.created
    assert not repeated.created
    assert repeated.reading.pk == result.reading.pk
    with pytest.raises(ReadingHistoryExistsError):
        create_initial_reading(
            user=user, book=book, status=Reading.Status.READING, completed_on=None
        )


def test_rereading_preserves_completed_history_and_state_transitions(
    user, book
) -> None:
    completed = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    rereading = create_rereading(
        user=user,
        source_reading=completed,
        status=Reading.Status.READING,
        completed_on=None,
    )
    changed = change_reading_state(
        user=user,
        reading=rereading.reading,
        status=Reading.Status.COMPLETED,
        completed_on=date.today() - timedelta(days=1),
    )
    updated = update_completion_date(
        user=user,
        reading=changed,
        completed_on=date.today(),
    )

    assert rereading.created
    assert Reading.objects.filter(user=user, book=book).count() == 2
    assert updated.completed_on == date.today()
    change_reading_state(
        user=user,
        reading=updated,
        status=Reading.Status.WANT_TO_READ,
        completed_on=None,
    )
    assert Reading.objects.get(pk=updated.pk).completed_on is None


def test_completed_to_active_rejects_existing_active_and_interview_lock(
    user, book, monkeypatch
) -> None:
    completed = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    Reading.objects.create(user=user, book=book, status=Reading.Status.READING)

    with pytest.raises(ActiveReadingExistsError):
        change_reading_state(
            user=user,
            reading=completed,
            status=Reading.Status.WANT_TO_READ,
            completed_on=None,
        )
    Reading.objects.filter(user=user, book=book, status=Reading.Status.READING).delete()
    monkeypatch.setattr("readings.services.has_started_interview", lambda reading: True)
    with pytest.raises(ReadingLockedError):
        update_completion_date(
            user=user,
            reading=completed,
            completed_on=date.today() - timedelta(days=1),
        )
    completed.refresh_from_db()
    assert completed.completed_on == date.today()


def test_interview_lock_preserves_completed_reading_when_cancelling(
    user, book, monkeypatch
) -> None:
    completed = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    monkeypatch.setattr("readings.services.has_started_interview", lambda reading: True)

    with pytest.raises(ReadingLockedError):
        change_reading_state(
            user=user,
            reading=completed,
            status=Reading.Status.READING,
            completed_on=None,
        )

    completed.refresh_from_db()
    assert completed.status == Reading.Status.COMPLETED
    assert completed.completed_on == date.today()


def test_completed_state_resubmission_does_not_change_completion_date(
    user, book
) -> None:
    completed = Reading.objects.create(
        user=user,
        book=book,
        status=Reading.Status.COMPLETED,
        completed_on=date.today() - timedelta(days=1),
    )

    unchanged = change_reading_state(
        user=user,
        reading=completed,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )

    assert unchanged.completed_on == date.today() - timedelta(days=1)


@pytest.mark.django_db(transaction=True)
def test_concurrent_initial_creation_reuses_one_active_reading(user, book) -> None:
    barrier = Barrier(2)

    def create_from_separate_connection() -> int:
        close_old_connections()
        try:
            barrier.wait()
            result = create_initial_reading(
                user=user,
                book=book,
                status=Reading.Status.READING,
                completed_on=None,
            )
            return result.reading.pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        reading_ids = list(
            executor.map(lambda _: create_from_separate_connection(), range(2))
        )

    assert len(set(reading_ids)) == 1
    assert Reading.objects.filter(user=user, book=book).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_rereading_reuses_one_active_reading(user, book) -> None:
    completed = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    barrier = Barrier(2)

    def create_from_separate_connection() -> tuple[int, bool]:
        close_old_connections()
        try:
            barrier.wait()
            result = create_rereading(
                user=user,
                source_reading=completed,
                status=Reading.Status.READING,
                completed_on=None,
            )
            return result.reading.pk, result.created
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: create_from_separate_connection(), range(2))
        )

    reading_ids = {reading_id for reading_id, _created in results}
    assert len(reading_ids) == 1
    assert sorted(created for _reading_id, created in results) == [False, True]
    assert (
        Reading.objects.filter(
            user=user,
            book=book,
            status__in=(Reading.Status.WANT_TO_READ, Reading.Status.READING),
        ).count()
        == 1
    )
    assert Reading.objects.filter(user=user, book=book).count() == 2
