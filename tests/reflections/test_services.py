from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections

from books.models import Book
from integrations.llm.contracts import (
    GeneratedQuestion,
    QuestionGenerationRejected,
    QuestionGenerationUnavailable,
)
from integrations.llm.fake import FakeQuestionProvider
from knowledge.models import BookKnowledge, KnowledgeKind
from readings.models import Reading
from readings.services import ReadingLockedError, update_completion_date
from reflections.models import Interview, InterviewTurn
from reflections.services import (
    FirstAnswerConflict,
    InterviewDestination,
    InterviewPolicyError,
    ensure_first_question,
    get_interview_destination,
    save_first_answer,
    start_interview,
)


@pytest.fixture
def completed_reading(django_user_model) -> Reading:
    user = django_user_model.objects.create_user(username="interview-service")
    book = Book.objects.create(isbn13="9788937834795", title="Interview 서비스")
    return Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )


def test_start_is_idempotent_snapshots_readiness_and_locks_reading(
    completed_reading,
) -> None:
    BookKnowledge.objects.create(
        book=completed_reading.book, kind=KnowledgeKind.THEME, content="주제"
    )
    created = start_interview(user=completed_reading.user, reading=completed_reading)
    repeated = start_interview(user=completed_reading.user, reading=completed_reading)

    assert created.created
    assert created.destination is InterviewDestination.INTERVIEW
    assert created.interview.knowledge_readiness == Interview.KnowledgeReadiness.READY
    assert not repeated.created
    assert repeated.interview.pk == created.interview.pk
    with pytest.raises(ReadingLockedError):
        update_completion_date(
            user=completed_reading.user,
            reading=completed_reading,
            completed_on=date.today(),
        )


def test_start_allows_limited_readiness(completed_reading) -> None:
    result = start_interview(user=completed_reading.user, reading=completed_reading)

    assert (
        result.interview.knowledge_readiness
        == Interview.KnowledgeReadiness.READY_LIMITED
    )


def test_start_rejects_unsaved_foreign_owned_and_incomplete_readings(
    completed_reading, django_user_model
) -> None:
    with pytest.raises(InterviewPolicyError):
        start_interview(user=completed_reading.user, reading=Reading())
    other_user = django_user_model.objects.create_user(username="other-service")
    with pytest.raises(InterviewPolicyError):
        start_interview(user=other_user, reading=completed_reading)
    completed_reading.status = Reading.Status.READING
    completed_reading.completed_on = None
    completed_reading.save()
    with pytest.raises(InterviewPolicyError):
        start_interview(user=completed_reading.user, reading=completed_reading)


def test_readiness_snapshot_and_destination_validation(completed_reading) -> None:
    BookKnowledge.objects.create(
        book=completed_reading.book, kind=KnowledgeKind.THEME, content="주제"
    )
    result = start_interview(user=completed_reading.user, reading=completed_reading)
    BookKnowledge.objects.filter(book=completed_reading.book).delete()
    result.interview.refresh_from_db()

    assert result.interview.knowledge_readiness == Interview.KnowledgeReadiness.READY
    result.interview.status = "INVALID"
    with pytest.raises(InterviewPolicyError):
        get_interview_destination(result.interview)


@pytest.mark.django_db(transaction=True)
def test_concurrent_starts_converge_to_one_interview(completed_reading) -> None:
    barrier = Barrier(2)

    def start_from_separate_connection() -> tuple[int, bool]:
        close_old_connections()
        try:
            barrier.wait()
            result = start_interview(
                user=completed_reading.user, reading=completed_reading
            )
            return result.interview.pk, result.created
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: start_from_separate_connection(), range(2))
        )

    assert len({interview_id for interview_id, _created in results}) == 1
    assert sorted(created for _interview_id, created in results) == [False, True]
    assert Interview.objects.filter(reading=completed_reading).count() == 1


def test_unexpected_database_error_rolls_back_and_a_retry_can_start(
    completed_reading, monkeypatch
) -> None:
    original_save = Interview.save
    original_book_id = completed_reading.book_id

    def fail_insert(self, *args, **kwargs) -> None:
        raise IntegrityError("unexpected database failure")

    monkeypatch.setattr(Interview, "save", fail_insert)
    with pytest.raises(IntegrityError):
        start_interview(user=completed_reading.user, reading=completed_reading)

    completed_reading.refresh_from_db()
    assert Interview.objects.filter(reading=completed_reading).count() == 0
    assert InterviewTurn.objects.count() == 0
    assert completed_reading.book_id == original_book_id
    monkeypatch.setattr(Interview, "save", original_save)

    retried = start_interview(user=completed_reading.user, reading=completed_reading)

    assert retried.created
    assert Interview.objects.filter(reading=completed_reading).count() == 1


def test_only_reading_one_to_one_conflicts_are_recoverable() -> None:
    class Diagnostics:
        constraint_name = "another_constraint"

    class DatabaseCause(Exception):
        diag = Diagnostics()

    error = IntegrityError()
    error.__cause__ = DatabaseCause()

    from reflections.services import _is_reading_one_to_one_conflict

    assert not _is_reading_one_to_one_conflict(error)

    Diagnostics.constraint_name = "reflections_interview_reading_id_key"
    assert _is_reading_one_to_one_conflict(error)


def test_first_question_is_saved_once_and_reused(completed_reading) -> None:
    interview = start_interview(
        user=completed_reading.user, reading=completed_reading
    ).interview
    provider = FakeQuestionProvider()

    created = ensure_first_question(
        user=completed_reading.user, interview=interview, provider=provider
    )
    reused = ensure_first_question(
        user=completed_reading.user, interview=interview, provider=provider
    )

    assert created.sequence == 1
    assert created.question.endswith("?")
    assert reused.pk == created.pk
    assert len(provider.contexts) == 1
    assert InterviewTurn.objects.filter(interview=interview, sequence=1).count() == 1


def test_first_answer_is_saved_once_and_same_value_is_idempotent(
    completed_reading,
) -> None:
    interview = start_interview(
        user=completed_reading.user, reading=completed_reading
    ).interview
    turn = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 남았나요?"
    )

    saved = save_first_answer(
        user=completed_reading.user, interview=interview, answer="처음 적은 답변"
    )
    repeated = save_first_answer(
        user=completed_reading.user, interview=interview, answer="처음 적은 답변"
    )

    assert saved.turn.pk == turn.pk
    assert saved.saved
    assert not repeated.saved
    with pytest.raises(FirstAnswerConflict) as error:
        save_first_answer(
            user=completed_reading.user, interview=interview, answer="다른 답변"
        )
    assert error.value.turn.answer == "처음 적은 답변"
    assert InterviewTurn.objects.get(pk=turn.pk).answer == "처음 적은 답변"


@pytest.mark.parametrize(
    "provider",
    [
        FakeQuestionProvider(error=QuestionGenerationUnavailable()),
        FakeQuestionProvider(
            result=GeneratedQuestion(question="질문입니다. 또 묻나요?")
        ),
        FakeQuestionProvider(result=GeneratedQuestion(question="물음표가 없습니다.")),
    ],
)
def test_failed_or_invalid_first_question_never_creates_turn(
    completed_reading, provider
) -> None:
    interview = start_interview(
        user=completed_reading.user, reading=completed_reading
    ).interview

    with pytest.raises((QuestionGenerationUnavailable, QuestionGenerationRejected)):
        ensure_first_question(
            user=completed_reading.user, interview=interview, provider=provider
        )

    assert InterviewTurn.objects.filter(interview=interview).count() == 0
