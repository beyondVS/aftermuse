from dataclasses import dataclass
from enum import StrEnum

from django.db import IntegrityError, transaction

from integrations.llm.contracts import (
    QuestionGenerationRejected,
    QuestionProvider,
)
from knowledge.services import BookKnowledgeReadiness, get_book_knowledge_readiness
from readings.models import Reading
from reflections.models import Interview, InterviewTurn

_READING_UNIQUE_CONSTRAINT = "reflections_interview_reading_id_key"


class InterviewDestination(StrEnum):
    """Interview 상태에서 사용자가 이어갈 수 있는 다음 단계다."""

    INTERVIEW = "INTERVIEW"
    REFLECTION_READY = "REFLECTION_READY"
    REFLECTION_COMPLETED = "REFLECTION_COMPLETED"


class InterviewPolicyError(Exception):
    """시작 흐름에서 안전하게 표시할 수 있는 정책 오류다."""


@dataclass(frozen=True, slots=True)
class InterviewStartResult:
    """생성 또는 재사용한 Interview와 현재 목적지를 전달한다."""

    interview: Interview
    created: bool
    destination: InterviewDestination


def get_interview_destination(interview: Interview) -> InterviewDestination:
    """현재 Interview 상태를 후속 화면 목적지로 변환한다."""
    destinations = {
        Interview.Status.IN_PROGRESS: InterviewDestination.INTERVIEW,
        Interview.Status.REFLECTION_READY: InterviewDestination.REFLECTION_READY,
        Interview.Status.COMPLETED: InterviewDestination.REFLECTION_COMPLETED,
    }
    try:
        return destinations[interview.status]
    except KeyError as error:
        raise InterviewPolicyError() from error


def start_interview(*, user, reading: Reading) -> InterviewStartResult:
    """소유한 완독 Reading을 잠근 뒤 Interview를 원자적으로 생성 또는 재사용한다."""
    if not isinstance(reading, Reading) or reading.pk is None:
        raise InterviewPolicyError()
    try:
        with transaction.atomic():
            locked_reading = (
                Reading.objects.select_for_update()
                .select_related("book")
                .filter(pk=reading.pk, user=user)
                .first()
            )
            if locked_reading is None or (
                locked_reading.status != Reading.Status.COMPLETED
                or locked_reading.completed_on is None
            ):
                raise InterviewPolicyError()
            existing = (
                Interview.objects.select_related("book")
                .filter(reading=locked_reading)
                .first()
            )
            if existing is not None:
                _validate_existing_interview(existing, locked_reading)
                return InterviewStartResult(
                    existing,
                    created=False,
                    destination=get_interview_destination(existing),
                )
            readiness = get_book_knowledge_readiness(locked_reading.book)
            if readiness not in {
                BookKnowledgeReadiness.READY,
                BookKnowledgeReadiness.READY_LIMITED,
            }:
                raise InterviewPolicyError()
            interview = Interview(
                reading=locked_reading,
                book=locked_reading.book,
                knowledge_readiness=readiness.value,
                status=Interview.Status.IN_PROGRESS,
            )
            interview.full_clean(validate_unique=False, validate_constraints=False)
            interview.save(force_insert=True)
            return InterviewStartResult(
                interview, created=True, destination=InterviewDestination.INTERVIEW
            )
    except IntegrityError as error:
        if not _is_reading_one_to_one_conflict(error):
            raise
        existing = (
            Interview.objects.select_related("book")
            .filter(reading_id=reading.pk)
            .first()
        )
        if existing is None:
            raise error
        _validate_existing_interview(existing, reading)
        return InterviewStartResult(
            existing, created=False, destination=get_interview_destination(existing)
        )


def _validate_existing_interview(interview: Interview, reading: Reading) -> None:
    if interview.book_id != reading.book_id:
        raise InterviewPolicyError()


def _is_reading_one_to_one_conflict(error: IntegrityError) -> bool:
    """같은 Reading의 Interview 유일성 충돌만 멱등 재시도로 처리한다."""
    cause = error.__cause__
    diagnostics = getattr(cause, "diag", None)
    return getattr(diagnostics, "constraint_name", None) == _READING_UNIQUE_CONSTRAINT


def ensure_first_question(
    *, user, interview: Interview, provider: QuestionProvider
) -> InterviewTurn:
    """첫 Turn을 재사용하거나 provider 호출 뒤 한 번만 안전하게 저장한다."""
    prepared = _get_valid_interview(user=user, interview=interview)
    existing = InterviewTurn.objects.filter(interview=prepared, sequence=1).first()
    if existing is not None:
        return existing

    from reflections.context import build_interview_question_context

    generated = provider.generate_first_question(
        build_interview_question_context(interview=prepared)
    )
    question = _validate_first_question(generated.question)
    try:
        with transaction.atomic():
            locked = (
                Interview.objects.select_for_update()
                .select_related("reading", "book")
                .filter(pk=prepared.pk, reading__user=user)
                .first()
            )
            if locked is None:
                raise InterviewPolicyError()
            _validate_interview_state(locked)
            existing = InterviewTurn.objects.filter(
                interview=locked, sequence=1
            ).first()
            if existing is not None:
                return existing
            return InterviewTurn.objects.create(
                interview=locked, sequence=1, question=question
            )
    except IntegrityError as error:
        existing = InterviewTurn.objects.filter(
            interview_id=prepared.pk, sequence=1
        ).first()
        if existing is not None:
            return existing
        raise error


def _get_valid_interview(*, user, interview: Interview) -> Interview:
    if not isinstance(interview, Interview) or interview.pk is None:
        raise InterviewPolicyError()
    prepared = (
        Interview.objects.select_related("reading", "book")
        .filter(pk=interview.pk, reading__user=user)
        .first()
    )
    if prepared is None:
        raise InterviewPolicyError()
    _validate_interview_state(prepared)
    return prepared


def _validate_interview_state(interview: Interview) -> None:
    if (
        interview.book_id != interview.reading.book_id
        or interview.status != Interview.Status.IN_PROGRESS
    ):
        raise InterviewPolicyError()


def _validate_first_question(question: object) -> str:
    """저장 전 질문의 줄 수, 길이, 문장 종결 조건을 강제한다."""
    if not isinstance(question, str):
        raise QuestionGenerationRejected()
    normalized = question.strip()
    if (
        not normalized
        or len(normalized) > 300
        or "\n" in normalized
        or not normalized.endswith(("?", "？"))
        or normalized.count("?") + normalized.count("？") != 1
    ):
        raise QuestionGenerationRejected()
    return normalized
