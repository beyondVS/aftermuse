"""Django 설정으로 첫 질문 Provider를 안전하게 선택한다."""

from django.conf import settings

from integrations.llm.contracts import (
    QuestionGenerationConfigurationError,
    QuestionProvider,
)
from integrations.llm.fake import FakeQuestionProvider


def get_question_provider() -> QuestionProvider:
    """현재 설정의 Provider를 만들고 알 수 없는 이름은 실행 전에 거부한다."""
    provider_name = settings.LLM_PROVIDER.strip().lower()
    if provider_name == "fake":
        return FakeQuestionProvider()
    raise QuestionGenerationConfigurationError
