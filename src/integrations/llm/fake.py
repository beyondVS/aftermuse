"""Network 없이 Interview LLM 결과를 재현하는 결정적 fake다."""

from integrations.llm.contracts import (
    AnswerAnalysisContext,
    AnswerAnalysisError,
    GeneratedQuestion,
    InterviewQuestionContext,
    ProposedAnswerAnalysis,
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


class FakeAnswerAnalysisProvider:
    """답변 분석 결과와 오류를 network 없이 결정적으로 재현한다."""

    def __init__(
        self,
        *,
        result: ProposedAnswerAnalysis | None = None,
        error: AnswerAnalysisError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.contexts: list[AnswerAnalysisContext] = []

    def analyze_answer(self, context: AnswerAnalysisContext) -> ProposedAnswerAnalysis:
        """Context를 기록하고 설정된 분석 결과 또는 오류를 반환한다."""
        self.contexts.append(context)
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        return ProposedAnswerAnalysis(
            meaning=context.answer.strip(),
            low_information=False,
            coverage_patch=(),
        )
