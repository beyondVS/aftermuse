"""첫 Interview Turn에 안전하게 전달할 Context를 구성한다."""

from integrations.llm.contracts import InterviewQuestionContext, QuestionPolicy
from knowledge.services import list_book_knowledge
from reflections.models import Interview
from reflections.services import InterviewPolicyError


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
