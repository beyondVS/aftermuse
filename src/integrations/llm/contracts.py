"""Interview LLM Provider가 공유하는 불변 계약과 안전한 오류 경계다."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol


class QuestionPolicy(StrEnum):
    """질문 생성 시 애플리케이션이 Provider에 부여하는 신뢰된 정책이다."""

    KNOWLEDGE_GROUNDED = "knowledge_grounded"
    MEMORY_CENTERED = "memory_centered"


@dataclass(frozen=True, slots=True)
class InterviewQuestionContext:
    """첫 질문 생성에 허용된 읽기 전용 Context payload다."""

    book_title: str
    authors: str
    publisher: str
    reading_status: str
    completed_on: date | None
    knowledge_readiness: str
    knowledge_claims: tuple[str, ...]
    policy: QuestionPolicy


@dataclass(frozen=True, slots=True)
class GeneratedQuestion:
    """Provider가 반환한 아직 영속화되지 않은 질문 후보다."""

    question: str


class QuestionProvider(Protocol):
    """외부 Provider와 무관하게 첫 질문 후보를 생성하는 경계다."""

    def generate_first_question(
        self, context: InterviewQuestionContext
    ) -> GeneratedQuestion:
        """주어진 Context로 첫 질문 후보 하나를 생성한다."""


@dataclass(frozen=True, slots=True)
class CurrentCoverageItem:
    """답변 분석에 전달하는 한 Core Coverage 축의 현재 상태다."""

    axis: str
    status: str


@dataclass(frozen=True, slots=True)
class AnswerAnalysisContext:
    """확정 답변 분석에 허용된 읽기 전용 Context payload다."""

    question_context: InterviewQuestionContext
    question: str
    answer: str
    current_coverage: tuple[CurrentCoverageItem, ...]


@dataclass(frozen=True, slots=True)
class ProposedCoverageChange:
    """Provider가 제안한 아직 신뢰되지 않은 Coverage 상승 후보다."""

    axis: object
    status: object
    evidence: object


@dataclass(frozen=True, slots=True)
class ProposedAnswerAnalysis:
    """Provider가 반환한 아직 검증되지 않은 답변 분석 제안이다."""

    meaning: object
    low_information: object
    coverage_patch: object


class AnswerAnalysisProvider(Protocol):
    """외부 Provider와 무관하게 답변 분석 후보를 생성하는 경계다."""

    def analyze_answer(self, context: AnswerAnalysisContext) -> ProposedAnswerAnalysis:
        """주어진 Context에서 구조화된 답변 분석 후보를 생성한다."""


@dataclass(frozen=True, slots=True)
class PreviousTurn:
    """후속 질문의 반복을 피하기 위해 허용된 이전 질문·답변이다."""

    question: str
    answer: str


@dataclass(frozen=True, slots=True)
class NextQuestionContext:
    """검증된 분석과 적용 예정 Coverage를 포함하는 읽기 전용 입력이다."""

    question_context: InterviewQuestionContext
    previous_turns: tuple[PreviousTurn, ...]
    question: str
    answer: str
    meaning: str | None
    low_information: bool
    coverage: tuple[CurrentCoverageItem, ...]


@dataclass(frozen=True, slots=True)
class ProposedNextQuestion:
    """질문 또는 명시적 질문 생략에 대한 신뢰되지 않은 제안이다."""

    kind: object
    question: object
    focus_axis: object
    grounding_quote: object
    skip_reason: object


class NextQuestionProvider(Protocol):
    """Interview 상태를 변경하지 않고 다음 질문만 제안한다."""

    def generate_next_question(
        self, context: NextQuestionContext
    ) -> ProposedNextQuestion:
        """질문 또는 질문 생략 제안 하나를 생성한다."""


class QuestionGenerationError(Exception):
    """질문 생성 실패를 안전한 사용자 상태로 변환하는 상위 오류다."""


class QuestionGenerationTimeout(QuestionGenerationError):
    """Provider 호출이 설정된 시간 안에 끝나지 않았음을 나타낸다."""


class QuestionGenerationUnavailable(QuestionGenerationError):
    """Provider 연결 또는 서비스 상태로 질문을 만들 수 없음을 나타낸다."""


class QuestionGenerationRejected(QuestionGenerationError):
    """Provider 출력이 질문 후보로 사용할 수 없음을 나타낸다."""


class QuestionGenerationConfigurationError(QuestionGenerationError):
    """선택한 질문 Provider의 안전한 실행 설정이 없음을 나타낸다."""


class AnswerAnalysisError(Exception):
    """답변 분석 실패를 안전한 application 오류로 변환하는 상위 오류다."""


class AnswerAnalysisTimeout(AnswerAnalysisError):
    """Provider가 설정된 시간 안에 답변 분석을 끝내지 못했다."""


class AnswerAnalysisUnavailable(AnswerAnalysisError):
    """Provider 연결 또는 서비스 상태로 답변을 분석할 수 없다."""


class AnswerAnalysisRejected(AnswerAnalysisError):
    """Provider 출력을 안전한 답변 분석 결과로 사용할 수 없다."""


class AnswerAnalysisConfigurationError(AnswerAnalysisError):
    """선택한 분석 Provider의 안전한 실행 설정이 없다."""
