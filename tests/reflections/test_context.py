from datetime import date

import pytest

from books.models import Book
from knowledge.models import BookKnowledge, KnowledgeKind
from readings.models import Reading
from reflections.context import build_interview_question_context
from reflections.models import Interview


@pytest.fixture
def interview(django_user_model) -> Interview:
    user = django_user_model.objects.create_user(username="context-owner")
    book = Book.objects.create(
        isbn13="9788937834701", title="Context 책", authors="저자", publisher="출판사"
    )
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    return Interview.objects.create(
        reading=reading,
        book=book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )


def test_ready_context_contains_only_stably_ordered_book_claims(interview) -> None:
    BookKnowledge.objects.create(
        book=interview.book, kind=KnowledgeKind.THEME, content="두 번째 주제"
    )
    BookKnowledge.objects.create(
        book=interview.book, kind=KnowledgeKind.ARGUMENT, content="첫 번째 논점"
    )

    context = build_interview_question_context(interview=interview)

    assert context.book_title == "Context 책"
    assert context.knowledge_claims == ("첫 번째 논점", "두 번째 주제")
    assert context.policy.value == "knowledge_grounded"
    with pytest.raises(AttributeError):
        context.book_title = "변경"  # type: ignore[misc]


def test_limited_context_excludes_claims_even_when_book_has_them(interview) -> None:
    BookKnowledge.objects.create(
        book=interview.book, kind=KnowledgeKind.THEME, content="포함하면 안 되는 Claim"
    )
    interview.knowledge_readiness = Interview.KnowledgeReadiness.READY_LIMITED
    interview.save()

    context = build_interview_question_context(interview=interview)

    assert context.knowledge_claims == ()
    assert context.policy.value == "memory_centered"
