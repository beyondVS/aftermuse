from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from books.models import Book
from readings.models import Reading
from reflections.models import Interview, InterviewTurn


@pytest.fixture
def interview(django_user_model) -> Interview:
    user = django_user_model.objects.create_user(username="interview-model")
    book = Book.objects.create(isbn13="9788937834793", title="Interview 모델")
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    return Interview.objects.create(
        reading=reading,
        book=book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )


def test_interview_relationships_are_immutable_but_status_can_change(interview) -> None:
    interview.status = Interview.Status.REFLECTION_READY
    interview.full_clean()
    interview.save()
    other_book = Book.objects.create(isbn13="9788937834794", title="다른 책")
    interview.book = other_book

    with pytest.raises(ValidationError):
        interview.full_clean()

    interview.refresh_from_db()
    assert interview.book_id != other_book.pk


def test_turn_orders_and_rejects_invalid_sequences_or_questions(interview) -> None:
    turn = InterviewTurn(interview=interview, sequence=1, question=" 첫 질문 ")
    turn.full_clean()
    turn.save()
    assert turn.question == "첫 질문"
    with pytest.raises(IntegrityError), transaction.atomic():
        InterviewTurn.objects.create(interview=interview, sequence=1, question="중복")
    with pytest.raises(ValidationError):
        InterviewTurn(interview=interview, sequence=0, question=" ").full_clean()


def test_interview_database_constraints_and_book_protection(interview) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Interview.objects.filter(pk=interview.pk).update(status="INVALID")
    with pytest.raises(IntegrityError), transaction.atomic():
        Interview.objects.filter(pk=interview.pk).update(knowledge_readiness="INVALID")
    with pytest.raises(ProtectedError):
        interview.book.delete()


def test_turn_preserves_nullable_answers_and_sequence_order(interview) -> None:
    later = InterviewTurn.objects.create(
        interview=interview, sequence=2, question="두 번째 질문", answer=None
    )
    first = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="첫 번째 질문", answer="답변"
    )

    turns = list(interview.turns.all())

    assert [turn.pk for turn in turns] == [first.pk, later.pk]
    assert later.answer is None


def test_turn_answer_validation_preserves_first_confirmed_value(interview) -> None:
    turn = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="첫 번째 질문", answer=None
    )
    turn.answer = "가" * 2000
    turn.full_clean()
    turn.save()
    turn.answer = "다른 답변"

    with pytest.raises(ValidationError):
        turn.full_clean()

    assert InterviewTurn.objects.get(pk=turn.pk).answer == "가" * 2000
    with pytest.raises(ValidationError):
        InterviewTurn(
            interview=interview, sequence=2, question="두 번째 질문", answer=" \n"
        ).full_clean()
