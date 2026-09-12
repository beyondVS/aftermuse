"""Django 설정으로 Interview LLM Provider를 안전하게 선택한다."""

from django.conf import settings

from integrations.llm.contracts import (
    AnswerAnalysisConfigurationError,
    AnswerAnalysisProvider,
    NextQuestionProvider,
    QuestionGenerationConfigurationError,
    QuestionProvider,
)
from integrations.llm.extra import GeminiInterviewProvider, OllamaInterviewProvider
from integrations.llm.fake import (
    FakeAnswerAnalysisProvider,
    FakeNextQuestionProvider,
    FakeQuestionProvider,
)
from integrations.llm.openai import (
    OpenAIAnswerAnalysisProvider,
    OpenAINextQuestionProvider,
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
    if provider_name == "gemini":
        return GeminiInterviewProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
        )
    if provider_name == "ollama":
        return OllamaInterviewProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
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
    if provider_name == "gemini":
        try:
            return GeminiInterviewProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                timeout=settings.GEMINI_TIMEOUT_SECONDS,
            )
        except QuestionGenerationConfigurationError as error:
            raise AnswerAnalysisConfigurationError() from error
    if provider_name == "ollama":
        try:
            return OllamaInterviewProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            )
        except QuestionGenerationConfigurationError as error:
            raise AnswerAnalysisConfigurationError() from error
    raise AnswerAnalysisConfigurationError


def get_next_question_provider() -> NextQuestionProvider:
    """현재 설정으로 후속 질문 Provider를 선택한다."""
    provider_name = settings.LLM_PROVIDER.strip().lower()
    if provider_name == "fake":
        return FakeNextQuestionProvider()
    if provider_name == "openai":
        return OpenAINextQuestionProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
    if provider_name == "gemini":
        return GeminiInterviewProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
        )
    if provider_name == "ollama":
        return OllamaInterviewProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
        )
    raise QuestionGenerationConfigurationError
