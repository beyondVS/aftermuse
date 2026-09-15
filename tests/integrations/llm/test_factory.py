"""설정별 네 capability factory가 서로 독립적으로 선택되는지 검증한다."""

import pytest
from django.test import override_settings

from integrations.llm.contracts import (
    AnswerAnalysisConfigurationError,
    QuestionGenerationConfigurationError,
    ReflectionGenerationConfigurationError,
)
from integrations.llm.factory import (
    get_answer_analysis_provider,
    get_next_question_provider,
    get_question_provider,
    get_reflection_provider,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("fake", "Fake"),
        ("openai", "OpenAI"),
        ("gemini", "Gemini"),
        ("ollama", "Ollama"),
    ],
)
def test_all_factory_capabilities_select_provider(name, expected):
    with override_settings(
        LLM_PROVIDER=name,
        OPENAI_API_KEY="test",
        GEMINI_API_KEY="test",
        OLLAMA_BASE_URL="http://127.0.0.1:11434",
        OLLAMA_MODEL="local-test",
    ):
        providers = (
            get_question_provider(),
            get_answer_analysis_provider(),
            get_next_question_provider(),
            get_reflection_provider(),
        )
    assert all(type(provider).__name__.startswith(expected) for provider in providers)


def test_unknown_provider_rejected_for_all_capabilities():
    with override_settings(LLM_PROVIDER="unknown"):
        with pytest.raises(QuestionGenerationConfigurationError):
            get_question_provider()
        with pytest.raises(AnswerAnalysisConfigurationError):
            get_answer_analysis_provider()
        with pytest.raises(QuestionGenerationConfigurationError):
            get_next_question_provider()
        with pytest.raises(ReflectionGenerationConfigurationError):
            get_reflection_provider()


@pytest.mark.parametrize("name", ["openai", "gemini", "ollama"])
def test_analysis_factory_maps_configuration_error(name):
    with override_settings(
        LLM_PROVIDER=name,
        OPENAI_API_KEY="",
        GEMINI_API_KEY="",
        OLLAMA_BASE_URL="http://remote:11434",
    ):
        with pytest.raises(AnswerAnalysisConfigurationError):
            get_answer_analysis_provider()


@pytest.mark.parametrize("name", ["openai", "gemini", "ollama"])
def test_reflection_factory_maps_configuration_error(name):
    with override_settings(
        LLM_PROVIDER=name,
        OPENAI_API_KEY="",
        GEMINI_API_KEY="",
        OLLAMA_BASE_URL="http://remote:11434",
    ):
        with pytest.raises(ReflectionGenerationConfigurationError):
            get_reflection_provider()


def test_reflection_factory_no_fallback():
    """provider 구성 오류 시 자동 fallback하지 않고 즉시 거부한다."""
    with override_settings(
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="",
    ):
        with pytest.raises(ReflectionGenerationConfigurationError):
            get_reflection_provider()
