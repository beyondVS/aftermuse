from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from books.models import Book
from readings.models import Reading


class ReadingPolicyError(Exception):
    """사용자에게 안전하게 안내할 수 있는 Reading 정책 오류의 기반 클래스다."""


class ReadingHistoryExistsError(ReadingPolicyError):
    """첫 Reading 생성 대상에 이미 완독 이력이 있을 때 발생한다."""

    def __init__(self, reading: Reading) -> None:
        self.reading = reading


class ActiveReadingExistsError(ReadingPolicyError):
    """활성 Reading 충돌 시 기존 Reading을 전달한다."""

    def __init__(self, reading: Reading) -> None:
        self.reading = reading


class InvalidReadingTransitionError(ReadingPolicyError):
    """상태와 완독일 조합이 유효하지 않을 때 발생한다."""


class ReadingLockedError(ReadingPolicyError):
    """Interview가 시작되어 완독 정보 변경이 잠겼을 때 발생한다."""


@dataclass(frozen=True, slots=True)
class ReadingCreationResult:
    """새 Reading 생성 여부와 실제 열어야 할 Reading을 함께 제공한다."""

    reading: Reading
    created: bool


def create_initial_reading(
    *, user, book: Book, status: str, completed_on: date | None
) -> ReadingCreationResult:
    """이력이 없는 책에만 첫 Reading을 만들고 경쟁 요청을 재사용한다."""
    with transaction.atomic():
        _lock_user(user)
        readings = _user_book_readings(user, book)
        active_reading = _active_reading(readings)
        if active_reading is not None:
            return ReadingCreationResult(active_reading, created=False)
        if readings:
            raise ReadingHistoryExistsError(_latest_completed_reading(readings))
        return ReadingCreationResult(
            _create_reading(
                user=user, book=book, status=status, completed_on=completed_on
            ),
            created=True,
        )


def create_rereading(
    *, user, source_reading: Reading, status: str, completed_on: date | None
) -> ReadingCreationResult:
    """소유한 완독 Reading에서만 별도의 재독 경험을 시작한다."""
    with transaction.atomic():
        locked_user = _lock_user(user)
        source = (
            Reading.objects.select_for_update()
            .select_related("book")
            .filter(
                pk=source_reading.pk, user=locked_user, status=Reading.Status.COMPLETED
            )
            .first()
        )
        if source is None:
            raise ReadingHistoryExistsError(source_reading)
        readings = _user_book_readings(locked_user, source.book)
        active_reading = _active_reading(readings)
        if active_reading is not None:
            return ReadingCreationResult(active_reading, created=False)
        return ReadingCreationResult(
            _create_reading(
                user=locked_user,
                book=source.book,
                status=status,
                completed_on=completed_on,
            ),
            created=True,
        )


def change_reading_state(
    *, user, reading: Reading, status: str, completed_on: date | None
) -> Reading:
    """소유 Reading의 상태와 필요한 완독일을 하나의 transaction으로 변경한다."""
    with transaction.atomic():
        locked_reading = _lock_reading(user, reading)
        if locked_reading.status == status:
            return locked_reading
        if has_started_interview(locked_reading):
            raise ReadingLockedError()
        if status == Reading.Status.COMPLETED:
            _validate_state_date(status, completed_on)
        else:
            _validate_state_date(status, None)
            active_reading = (
                Reading.objects.select_for_update()
                .filter(
                    user=locked_reading.user,
                    book=locked_reading.book,
                    status__in=(Reading.Status.WANT_TO_READ, Reading.Status.READING),
                )
                .exclude(pk=locked_reading.pk)
                .first()
            )
            if active_reading is not None:
                raise ActiveReadingExistsError(active_reading)
        locked_reading.status = status
        locked_reading.completed_on = (
            completed_on if status == Reading.Status.COMPLETED else None
        )
        _save_reading(locked_reading)
        return locked_reading


def update_completion_date(*, user, reading: Reading, completed_on: date) -> Reading:
    """Interview가 시작되지 않은 완독 Reading의 날짜만 명시적으로 수정한다."""
    with transaction.atomic():
        locked_reading = _lock_reading(user, reading)
        if locked_reading.status != Reading.Status.COMPLETED:
            raise InvalidReadingTransitionError()
        if has_started_interview(locked_reading):
            raise ReadingLockedError()
        _validate_state_date(Reading.Status.COMPLETED, completed_on)
        locked_reading.completed_on = completed_on
        _save_reading(locked_reading)
        return locked_reading


def has_started_interview(reading: Reading) -> bool:
    """Day 05가 실제 Interview 조회로 대체할 잠금 확장 지점이다."""
    del reading
    return False


def _lock_user(user):
    return user.__class__.objects.select_for_update().get(pk=user.pk)


def _lock_reading(user, reading: Reading) -> Reading:
    locked_reading = (
        Reading.objects.select_for_update()
        .select_related("book", "user")
        .filter(pk=reading.pk, user=user)
        .first()
    )
    if locked_reading is None:
        raise ReadingHistoryExistsError(reading)
    return locked_reading


def _user_book_readings(user, book: Book) -> list[Reading]:
    return list(
        Reading.objects.select_for_update()
        .filter(user=user, book=book)
        .order_by("-completed_on", "-created_at", "-pk")
    )


def _active_reading(readings: list[Reading]) -> Reading | None:
    return next((reading for reading in readings if reading.is_active), None)


def _latest_completed_reading(readings: list[Reading]) -> Reading:
    return next(
        reading for reading in readings if reading.status == Reading.Status.COMPLETED
    )


def _create_reading(
    *, user, book: Book, status: str, completed_on: date | None
) -> Reading:
    _validate_state_date(status, completed_on)
    reading = Reading(user=user, book=book, status=status, completed_on=completed_on)
    try:
        _save_reading(reading)
    except IntegrityError as error:
        active_reading = (
            Reading.objects.filter(
                user=user,
                book=book,
                status__in=(Reading.Status.WANT_TO_READ, Reading.Status.READING),
            )
            .order_by("pk")
            .first()
        )
        if active_reading is None:
            raise error
        raise ActiveReadingExistsError(active_reading) from error
    return reading


def _save_reading(reading: Reading) -> None:
    try:
        reading.full_clean()
    except ValidationError as error:
        raise InvalidReadingTransitionError() from error
    reading.save()


def _validate_state_date(status: str, completed_on: date | None) -> None:
    valid_statuses = {choice.value for choice in Reading.Status}
    if status not in valid_statuses:
        raise InvalidReadingTransitionError()
    if status == Reading.Status.COMPLETED:
        if completed_on is None or completed_on > date.today():
            raise InvalidReadingTransitionError()
    elif completed_on is not None:
        raise InvalidReadingTransitionError()
