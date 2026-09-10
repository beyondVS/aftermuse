from datetime import date

import pytest

from books.models import Book
from knowledge.models import BookKnowledge, KnowledgeKind
from readings.models import Reading
from reflections.context import (
    build_answer_analysis_context,
    build_interview_question_context,
)
from reflections.models import Interview, InterviewTurn
from reflections.services import AnswerAnalysisPolicyError, InterviewPolicyError


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


def test_context_rejects_invalid_interview_state_and_excludes_other_book_claims(
    interview,
) -> None:
    other_book = Book.objects.create(isbn13="9788937834702", title="다른 책")
    BookKnowledge.objects.create(
        book=interview.book, kind=KnowledgeKind.THEME, content="현재 책 Claim"
    )
    BookKnowledge.objects.create(
        book=other_book, kind=KnowledgeKind.THEME, content="다른 책 Claim"
    )

    assert build_interview_question_context(interview=interview).knowledge_claims == (
        "현재 책 Claim",
    )
    interview.status = Interview.Status.COMPLETED
    with pytest.raises(InterviewPolicyError):
        build_interview_question_context(interview=interview)
    interview.status = Interview.Status.IN_PROGRESS
    interview.book = other_book
    with pytest.raises(InterviewPolicyError):
        build_interview_question_context(interview=interview)


def test_answer_analysis_context_preserves_answer_and_canonical_coverage(
    interview,
) -> None:
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="무엇이 남았나요?",
        answer="  원문 공백을 보존합니다  ",
    )
    interview.coverage["REACTION"] = "PARTIAL"
    interview.save(update_fields=("coverage", "updated_at"))

    context = build_answer_analysis_context(interview=interview, turn=turn)

    assert context.answer == "  원문 공백을 보존합니다  "
    assert tuple(item.axis for item in context.current_coverage) == (
        "MEMORY",
        "REACTION",
        "CONNECTION",
        "AFTERTHOUGHT",
    )
    assert context.current_coverage[1].status == "PARTIAL"


def test_answer_analysis_context_rejects_wrong_or_unanswered_turn(interview) -> None:
    unanswered = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문?"
    )
    other = Interview()

    with pytest.raises(AnswerAnalysisPolicyError):
        build_answer_analysis_context(interview=interview, turn=unanswered)
    with pytest.raises(AnswerAnalysisPolicyError):
        build_answer_analysis_context(interview=other, turn=unanswered)
