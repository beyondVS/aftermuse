"""첫 Interview Turn에 안전하게 전달할 Context를 구성한다."""

from integrations.llm.contracts import (
    AnswerAnalysisContext,
    CurrentCoverageItem,
    InterviewQuestionContext,
    QuestionPolicy,
)
from knowledge.services import list_book_knowledge
from reflections.models import (
    CORE_COVERAGE,
    Interview,
    InterviewTurn,
    is_canonical_coverage,
)
from reflections.services import AnswerAnalysisPolicyError, InterviewPolicyError


def build_interview_question_context(
    *, interview: Interview
) -> InterviewQuestionContext:
    """Interview의 준비 수준에 맞는 읽기 전용 질문 Context를 반환한다."""
    if (
        interview.pk is None
        or interview.reading_id is None
        or interview.book_id != interview.reading.book_id
        or interview.status != Interview.Status.IN_PROGRESS
    ):
        raise InterviewPolicyError()
    try:
        readiness = Interview.KnowledgeReadiness(interview.knowledge_readiness)
    except ValueError as error:
        raise InterviewPolicyError() from error
    claims = ()
    policy = QuestionPolicy.MEMORY_CENTERED
    if readiness is Interview.KnowledgeReadiness.READY:
        claims = tuple(claim.content for claim in list_book_knowledge(interview.book))
        policy = QuestionPolicy.KNOWLEDGE_GROUNDED
    return InterviewQuestionContext(
        book_title=interview.book.title,
        authors=interview.book.authors,
        publisher=interview.book.publisher,
        reading_status=interview.reading.status,
        completed_on=interview.reading.completed_on,
        knowledge_readiness=readiness.value,
        knowledge_claims=claims,
        policy=policy,
    )


def build_answer_analysis_context(
    *, interview: Interview, turn: InterviewTurn
) -> AnswerAnalysisContext:
    """검증된 Interview와 확정 Turn에서 비영속 분석 Context를 구성한다."""
    if (
        not isinstance(turn, InterviewTurn)
        or turn.pk is None
        or turn.interview_id != interview.pk
        or turn.answer is None
        or not is_canonical_coverage(interview.coverage)
    ):
        raise AnswerAnalysisPolicyError()
    try:
        question_context = build_interview_question_context(interview=interview)
    except InterviewPolicyError as error:
        raise AnswerAnalysisPolicyError() from error
    return AnswerAnalysisContext(
        question_context=question_context,
        question=turn.question,
        answer=turn.answer,
        current_coverage=tuple(
            CurrentCoverageItem(axis=axis.value, status=interview.coverage[axis.value])
            for axis in CORE_COVERAGE
        ),
    )
