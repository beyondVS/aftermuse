from datetime import date

import pytest

from integrations.llm.contracts import (
    AnswerAnalysisConfigurationError,
    AnswerAnalysisContext,
    AnswerAnalysisUnavailable,
    CurrentCoverageItem,
    InterviewQuestionContext,
    ProposedAnswerAnalysis,
    QuestionPolicy,
)
from integrations.llm.factory import get_answer_analysis_provider
from integrations.llm.fake import (
    DEFAULT_QUESTION,
    FakeAnswerAnalysisProvider,
    FakeQuestionProvider,
)


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


def test_analysis_fake_returns_configured_result_and_records_context() -> None:
    question_context = InterviewQuestionContext(
        book_title="책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=None,
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )
    context = AnswerAnalysisContext(
        question_context=question_context,
        question="무엇이 남았나요?",
        answer="결말이 허무했어요",
        current_coverage=(CurrentCoverageItem("REACTION", "UNCOVERED"),),
    )
    configured = ProposedAnswerAnalysis("허무함", False, ())
    provider = FakeAnswerAnalysisProvider(result=configured)

    assert provider.analyze_answer(context) is configured
    assert provider.contexts == [context]


def test_analysis_fake_replays_error_without_network() -> None:
    error = AnswerAnalysisUnavailable()
    provider = FakeAnswerAnalysisProvider(error=error)
    context = AnswerAnalysisContext(
        question_context=InterviewQuestionContext(
            "책",
            "",
            "",
            "COMPLETED",
            None,
            "READY_LIMITED",
            (),
            QuestionPolicy.MEMORY_CENTERED,
        ),
        question="질문?",
        answer="답변",
        current_coverage=(),
    )

    with pytest.raises(AnswerAnalysisUnavailable) as caught:
        provider.analyze_answer(context)

    assert caught.value is error


def test_analysis_factory_selects_fake_and_rejects_unknown_provider(settings) -> None:
    settings.LLM_PROVIDER = "fake"
    assert isinstance(get_answer_analysis_provider(), FakeAnswerAnalysisProvider)

    settings.LLM_PROVIDER = "unknown"
    with pytest.raises(AnswerAnalysisConfigurationError):
        get_answer_analysis_provider()
