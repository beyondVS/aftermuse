"""명시적으로 선택한 경우에만 실제 LLM 연결을 확인한다."""

import os

import pytest

from integrations.llm.contracts import (
    InterviewQuestionContext,
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


def test_gemini_live():
    key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "")
    if not key or not model:
        pytest.skip("GEMINI_API_KEY or GEMINI_MODEL is not configured")
    question = GeminiInterviewProvider(
        api_key=key,
        model=model,
        timeout=30,
    ).generate_first_question(_context())
    assert question.question.strip()


def test_ollama_live():
    model = os.environ.get("OLLAMA_MODEL", "")
    if os.environ.get("OLLAMA_LIVE_TEST") != "1" or not model:
        pytest.skip("OLLAMA_LIVE_TEST or OLLAMA_MODEL is not configured")
    question = OllamaInterviewProvider(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        model=model,
        timeout=120,
    ).generate_first_question(_context())
    assert question.question.strip()
