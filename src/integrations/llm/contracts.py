"""첫 인터뷰 질문 Provider가 공유하는 불변 계약과 안전한 오류 경계다."""

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
