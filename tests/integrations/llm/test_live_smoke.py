"""명시적으로 선택한 경우에만 실제 LLM 연결을 확인한다."""

import os

import pytest

from integrations.llm.contracts import (
    AnswerAnalysisContext,
    CurrentCoverageItem,
    InterviewQuestionContext,
    NextQuestionContext,
    QuestionPolicy,
)
from integrations.llm.extra import GeminiInterviewProvider, OllamaInterviewProvider

pytestmark = pytest.mark.live


def _context():
    return InterviewQuestionContext(
        "테스트 책",
        "",
        "",
        "COMPLETED",
        None,
        "READY_LIMITED",
        (),
        QuestionPolicy.MEMORY_CENTERED,
    )


def _smoke_three_tasks(provider):
    """실제 모델에서 중첩 배열과 nullable 후속 질문까지 확인한다."""
    context = _context()
    first = provider.generate_first_question(context)
    assert first.question.strip()
    coverage = tuple(
        CurrentCoverageItem(axis, "UNCOVERED")
        for axis in ("MEMORY", "REACTION", "CONNECTION", "AFTERTHOUGHT")
    )
    answer = "푸른 표지가 기억에 남았어요. 차분한 느낌이 들었어요."
    analysis = provider.analyze_answer(
        AnswerAnalysisContext(context, first.question, answer, coverage)
    )
    assert isinstance(analysis.low_information, bool)
    assert isinstance(analysis.coverage_patch, tuple)
    next_question = provider.generate_next_question(
        NextQuestionContext(
            context,
            (),
            first.question,
            answer,
            analysis.meaning if isinstance(analysis.meaning, str) else None,
            analysis.low_information,
            coverage,
        )
    )
    assert next_question.kind == "question"
    assert isinstance(next_question.question, str) and next_question.question.strip()


def test_gemini_live():
    key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "")
    if not key or not model:
        pytest.skip("GEMINI_API_KEY or GEMINI_MODEL is not configured")
    provider = GeminiInterviewProvider(
        api_key=key,
        model=model,
        timeout=30,
    )
    _smoke_three_tasks(provider)


def test_ollama_live():
    model = os.environ.get("OLLAMA_MODEL", "")
    if os.environ.get("OLLAMA_LIVE_TEST") != "1" or not model:
        pytest.skip("OLLAMA_LIVE_TEST or OLLAMA_MODEL is not configured")
    provider = OllamaInterviewProvider(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        model=model,
        timeout=120,
    )
    _smoke_three_tasks(provider)
