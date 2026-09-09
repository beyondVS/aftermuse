from datetime import date

from integrations.llm.contracts import InterviewQuestionContext, QuestionPolicy
from integrations.llm.fake import DEFAULT_QUESTION, FakeQuestionProvider


def test_fake_returns_question_and_records_exact_context() -> None:
    context = InterviewQuestionContext(
        book_title="책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=date(2026, 9, 9),
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )

    provider = FakeQuestionProvider()
    result = provider.generate_first_question(context)

    assert result.question == DEFAULT_QUESTION
    assert provider.contexts == [context]
