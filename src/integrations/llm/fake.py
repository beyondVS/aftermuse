"""Network 없이 첫 질문 Provider 결과를 재현하는 결정적 fake다."""

from integrations.llm.contracts import (
    GeneratedQuestion,
    InterviewQuestionContext,
    QuestionGenerationError,
)

DEFAULT_QUESTION = "이 책에서 가장 오래 남은 장면이나 생각은 무엇인가요?"


class FakeQuestionProvider:
    """테스트와 로컬 개발에서 결과 또는 오류를 고정해 반환하는 Provider다."""

    def __init__(
        self,
        *,
        result: GeneratedQuestion | None = None,
        error: QuestionGenerationError | None = None,
    ) -> None:
        self._result = result or GeneratedQuestion(question=DEFAULT_QUESTION)
        self._error = error
        self.contexts: list[InterviewQuestionContext] = []

    def generate_first_question(
        self, context: InterviewQuestionContext
    ) -> GeneratedQuestion:
        """Context를 기록하고 설정된 결과 또는 질문 생성 오류를 반환한다."""
        self.contexts.append(context)
        if self._error is not None:
            raise self._error
        return self._result
