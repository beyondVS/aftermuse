"""Network 없이 Interview LLM 결과를 재현하는 결정적 fake다."""

import re

from integrations.llm.contracts import (
    AnswerAnalysisContext,
    AnswerAnalysisError,
    GeneratedQuestion,
    InterviewQuestionContext,
    NextQuestionContext,
    ProposedAnswerAnalysis,
    ProposedNextQuestion,
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


class FakeNextQuestionProvider:
    """다음 질문 또는 오류를 외부 연결 없이 재현한다."""

    def __init__(
        self,
        *,
        result: ProposedNextQuestion | None = None,
        error: QuestionGenerationError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.contexts: list[NextQuestionContext] = []

    def generate_next_question(
        self, context: NextQuestionContext
    ) -> ProposedNextQuestion:
        """현재 답변과 미충족 축을 사용한 결정적 후보를 반환한다."""
        self.contexts.append(context)
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        gaps = tuple(item for item in context.coverage if item.status != "COVERED")
        if not gaps and context.low_information:
            return ProposedNextQuestion(
                "skip",
                None,
                None,
                None,
                "네 방향이 다뤄졌고 이 답변에는 추가 탐색 근거가 없습니다.",
            )
        if not gaps:
            gaps = context.coverage
        gap = (
            gaps[(len(context.previous_turns) + 1) % len(gaps)]
            if context.low_information
            else gaps[0]
        )
        prompts = {
            "MEMORY": "방금 이야기한 내용에서 특히 기억에 남는 부분은 무엇인가요?",
            "REACTION": "그 부분을 읽으며 어떤 반응이 들었나요?",
            "CONNECTION": "그 생각이 자신의 경험과 닿는 지점이 있나요?",
            "AFTERTHOUGHT": "책을 덮은 뒤에도 남아 있는 생각은 무엇인가요?",
        }
        if context.low_information:
            return ProposedNextQuestion(
                "question", prompts[gap.axis], gap.axis, None, None
            )
        quote = context.answer.strip()[:24]
        excerpt = re.sub(r"[.!?。！？\n]", " ", quote).strip()
        question = (
            f"‘{excerpt}’라고 하셨는데, 그 생각이 더 남은 이유는 무엇인가요?"
            if excerpt
            else prompts[gap.axis]
        )
        return ProposedNextQuestion("question", question, gap.axis, quote, None)
