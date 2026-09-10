"""Django 설정으로 Interview LLM Provider를 안전하게 선택한다."""

from django.conf import settings

from integrations.llm.contracts import (
    AnswerAnalysisConfigurationError,
    AnswerAnalysisProvider,
    QuestionGenerationConfigurationError,
    QuestionProvider,
)
from integrations.llm.fake import FakeAnswerAnalysisProvider, FakeQuestionProvider
from integrations.llm.openai import (
    OpenAIAnswerAnalysisProvider,
    OpenAIQuestionProvider,
)


def get_question_provider() -> QuestionProvider:
    """현재 설정의 Provider를 만들고 알 수 없는 이름은 실행 전에 거부한다."""
    provider_name = settings.LLM_PROVIDER.strip().lower()
    if provider_name == "fake":
        return FakeQuestionProvider()
    if provider_name == "openai":
        return OpenAIQuestionProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
    raise QuestionGenerationConfigurationError


def get_answer_analysis_provider() -> AnswerAnalysisProvider:
    """현재 설정으로 답변 분석 Provider를 만들고 알 수 없는 이름을 거부한다."""
    provider_name = settings.LLM_PROVIDER.strip().lower()
    if provider_name == "fake":
        return FakeAnswerAnalysisProvider()
    if provider_name == "openai":
        return OpenAIAnswerAnalysisProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
    raise AnswerAnalysisConfigurationError
