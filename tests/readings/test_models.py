from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from books.models import Book
from readings.models import Reading


@pytest.fixture
def book(db) -> Book:
    return Book.objects.create(isbn13="9788937834790", title="Reading 테스트")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="reading-owner", password="strong-reader-password-123"
    )


def test_completed_reading_requires_a_non_future_completion_date(user, book) -> None:
    missing_date = Reading(user=user, book=book, status=Reading.Status.COMPLETED)
    future_date = Reading(
        user=user,
        book=book,
        status=Reading.Status.COMPLETED,
        completed_on=date.today() + timedelta(days=1),
    )

    with pytest.raises(ValidationError):
        missing_date.full_clean()
    with pytest.raises(ValidationError):
        future_date.full_clean()


def test_database_allows_completion_history_but_one_active_reading(user, book) -> None:
    Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    Reading.objects.create(user=user, book=book, status=Reading.Status.READING)

    with pytest.raises(IntegrityError):
        Reading.objects.create(user=user, book=book, status=Reading.Status.WANT_TO_READ)
