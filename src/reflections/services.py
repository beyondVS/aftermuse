from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from integrations.llm.contracts import (
    AnswerAnalysisProvider,
    AnswerAnalysisRejected,
    ProposedAnswerAnalysis,
    ProposedCoverageChange,
    QuestionGenerationRejected,
    QuestionProvider,
)
from knowledge.services import BookKnowledgeReadiness, get_book_knowledge_readiness
from readings.models import Reading
from reflections.models import (
    CoreCoverageAxis,
    CoverageStatus,
    Interview,
    InterviewTurn,
    is_canonical_coverage,
)

_READING_UNIQUE_CONSTRAINT = "reflections_interview_reading_id_key"
_QUESTION_PROHIBITED_PATTERNS = (
    "관리자 권한",
    "시스템 상태",
    "상태를 변경",
    "크레딧",
    "웹 검색",
    "데이터베이스",
    "이전 지시를 무시",
)
_ANALYSIS_PROHIBITED_PATTERNS = (
    "이전 지시를 무시",
    "시스템 프롬프트",
    "관리자 권한",
    "API 키를 공개",
    "비밀값을 출력",
)
_ANSWER_MEANING_MAX_LENGTH = 1000
_ANSWER_EVIDENCE_MAX_LENGTH = 500


class InterviewDestination(StrEnum):
    """Interview 상태에서 사용자가 이어갈 수 있는 다음 단계다."""

    INTERVIEW = "INTERVIEW"
    REFLECTION_READY = "REFLECTION_READY"
    REFLECTION_COMPLETED = "REFLECTION_COMPLETED"


class InterviewPolicyError(Exception):
    """시작 흐름에서 안전하게 표시할 수 있는 정책 오류다."""


class CoveragePolicyError(Exception):
    """Coverage 대상, 입력 또는 상태 전환이 계약을 위반했다."""


class AnswerAnalysisPolicyError(Exception):
    """답변 분석 대상의 소유권, 관계 또는 상태가 계약을 위반했다."""


class FirstAnswerValidationError(Exception):
    """첫 답변이 저장 계약을 충족하지 않음을 나타낸다."""


class FirstAnswerPersistenceError(Exception):
    """답변 확정 중 복구 가능한 데이터베이스 오류가 발생했음을 나타낸다."""


class FirstAnswerConflict(Exception):
    """이미 다른 원문으로 확정된 첫 답변이 있음을 나타낸다."""

    def __init__(self, turn: InterviewTurn) -> None:
        self.turn = turn


@dataclass(frozen=True, slots=True)
class FirstAnswerSaveResult:
    """첫 답변 저장 또는 동일 값 재사용의 결과다."""

    turn: InterviewTurn
    saved: bool


@dataclass(frozen=True, slots=True)
class InterviewStartResult:
    """생성 또는 재사용한 Interview와 현재 목적지를 전달한다."""

    interview: Interview
    created: bool
    destination: InterviewDestination


@dataclass(frozen=True, slots=True)
class CoveragePatchItem:
    """한 Core Coverage 축에 적용할 목표 상태다."""

    axis: CoreCoverageAxis | str
    status: CoverageStatus | str


@dataclass(frozen=True, slots=True)
class CoverageSnapshot:
    """호출자와 저장 객체를 공유하지 않는 canonical Coverage 조회 결과다."""

    memory: CoverageStatus
    reaction: CoverageStatus
    connection: CoverageStatus
    afterthought: CoverageStatus

    def as_dict(self) -> dict[str, str]:
        """외부 변경이 내부 저장 상태에 영향을 주지 않는 복사본을 반환한다."""
        return {
            CoreCoverageAxis.MEMORY.value: self.memory.value,
            CoreCoverageAxis.REACTION.value: self.reaction.value,
            CoreCoverageAxis.CONNECTION.value: self.connection.value,
            CoreCoverageAxis.AFTERTHOUGHT.value: self.afterthought.value,
        }


@dataclass(frozen=True, slots=True)
class CoveragePatchResult:
    """Coverage patch 적용 뒤 최신 snapshot과 실제 변경 여부다."""

    snapshot: CoverageSnapshot
    changed: bool


@dataclass(frozen=True, slots=True)
class AnalyzedCoverageChange:
    """원문 근거가 확인된 한 Core Coverage 상승 후보다."""

    axis: CoreCoverageAxis
    status: CoverageStatus
    evidence: str


@dataclass(frozen=True, slots=True)
class AnswerAnalysisResult:
    """Application 검증을 통과한 비영속 답변 분석 결과다."""

    meaning: str | None
    low_information: bool
    coverage_patch: tuple[AnalyzedCoverageChange, ...]


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
    *,
    user,
    interview: Interview,
    provider: QuestionProvider | None = None,
    provider_factory: Callable[[], QuestionProvider] | None = None,
) -> InterviewTurn:
    """첫 Turn을 재사용하거나 provider 호출 뒤 한 번만 안전하게 저장한다."""
    prepared = _get_valid_interview(user=user, interview=interview)
    existing = InterviewTurn.objects.filter(interview=prepared, sequence=1).first()
    if existing is not None:
        return existing
    if provider is not None and provider_factory is not None:
        raise ValueError("provider와 provider_factory는 함께 지정할 수 없습니다.")
    if provider is None:
        if provider_factory is None:
            raise ValueError("provider 또는 provider_factory가 필요합니다.")
        provider = provider_factory()

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
        or any(marker in normalized[:-1] for marker in ".!。！？")
        or any(pattern in normalized for pattern in _QUESTION_PROHIBITED_PATTERNS)
    ):
        raise QuestionGenerationRejected()
    return normalized


def save_first_answer(
    *, user, interview: Interview, answer: object
) -> FirstAnswerSaveResult:
    """첫 답변을 한 번만 확정하고 같은 재제출은 멱등 처리한다."""
    validated_answer = _validate_first_answer(answer)
    try:
        with transaction.atomic():
            locked_interview = (
                Interview.objects.select_for_update()
                .select_related("reading", "book")
                .filter(pk=interview.pk, reading__user=user)
                .first()
            )
            if locked_interview is None:
                raise InterviewPolicyError()
            _validate_interview_state(locked_interview)
            turn = (
                InterviewTurn.objects.select_for_update()
                .filter(interview=locked_interview, sequence=1)
                .first()
            )
            if turn is None:
                raise InterviewPolicyError()
            if turn.answer is None:
                turn.answer = validated_answer
                turn.full_clean()
                turn.save(update_fields=("answer", "updated_at"))
                return FirstAnswerSaveResult(turn=turn, saved=True)
            if turn.answer == validated_answer:
                return FirstAnswerSaveResult(turn=turn, saved=False)
            raise FirstAnswerConflict(turn)
    except FirstAnswerConflict:
        raise
    except DatabaseError as error:
        raise FirstAnswerPersistenceError() from error


def _validate_first_answer(answer: object) -> str:
    """답변 원문을 바꾸지 않고 public 저장 범위만 확인한다."""
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 2000:
        raise FirstAnswerValidationError()
    return answer


def analyze_interview_answer(
    *,
    user,
    interview: Interview,
    turn: InterviewTurn,
    provider: AnswerAnalysisProvider | None = None,
    provider_factory: Callable[[], AnswerAnalysisProvider] | None = None,
) -> AnswerAnalysisResult:
    """확정 답변을 분석하고 검증된 비영속 결과만 반환한다."""
    if provider is not None and provider_factory is not None:
        raise ValueError("provider와 provider_factory는 함께 지정할 수 없습니다.")
    prepared, prepared_turn = _get_answer_analysis_target(
        user=user, interview=interview, turn=turn
    )
    if provider is None:
        if provider_factory is None:
            from integrations.llm.factory import get_answer_analysis_provider

            provider_factory = get_answer_analysis_provider
        provider = provider_factory()

    from reflections.context import build_answer_analysis_context

    context = build_answer_analysis_context(interview=prepared, turn=prepared_turn)
    proposed = provider.analyze_answer(context)
    return _validate_answer_analysis(proposed, context.answer, prepared.coverage)


def _get_answer_analysis_target(
    *, user, interview: Interview, turn: InterviewTurn
) -> tuple[Interview, InterviewTurn]:
    """소유권과 관계를 숨긴 채 DB의 최신 분석 대상을 준비한다."""
    if (
        not isinstance(interview, Interview)
        or interview.pk is None
        or not isinstance(turn, InterviewTurn)
        or turn.pk is None
    ):
        raise AnswerAnalysisPolicyError()
    prepared = (
        Interview.objects.select_related("reading", "book")
        .filter(pk=interview.pk, reading__user=user)
        .first()
    )
    if (
        prepared is None
        or prepared.book_id != prepared.reading.book_id
        or prepared.status != Interview.Status.IN_PROGRESS
        or not is_canonical_coverage(prepared.coverage)
    ):
        raise AnswerAnalysisPolicyError()
    prepared_turn = InterviewTurn.objects.filter(pk=turn.pk, interview=prepared).first()
    if (
        prepared_turn is None
        or not isinstance(prepared_turn.question, str)
        or not prepared_turn.question.strip()
        or not isinstance(prepared_turn.answer, str)
        or not prepared_turn.answer.strip()
        or len(prepared_turn.answer) > 2000
    ):
        raise AnswerAnalysisPolicyError()
    return prepared, prepared_turn


def _validate_answer_analysis(
    proposed: object, answer: str, current_coverage: dict[str, str]
) -> AnswerAnalysisResult:
    """Provider 제안을 부분 수용 없이 trusted 분석 결과로 변환한다."""
    if not isinstance(proposed, ProposedAnswerAnalysis) or not isinstance(
        proposed.low_information, bool
    ):
        raise AnswerAnalysisRejected()
    patch = proposed.coverage_patch
    if (
        not isinstance(patch, Sequence)
        or isinstance(patch, (str, bytes))
        or len(patch) > len(CoreCoverageAxis)
    ):
        raise AnswerAnalysisRejected()
    if proposed.low_information:
        if proposed.meaning is not None or patch:
            raise AnswerAnalysisRejected()
        return AnswerAnalysisResult(None, True, ())
    meaning = _validate_analysis_text(
        proposed.meaning, maximum=_ANSWER_MEANING_MAX_LENGTH
    )
    validated: dict[CoreCoverageAxis, AnalyzedCoverageChange] = {}
    for item in patch:
        if not isinstance(item, ProposedCoverageChange):
            raise AnswerAnalysisRejected()
        try:
            axis = CoreCoverageAxis(item.axis)
            status = CoverageStatus(item.status)
            current_status = CoverageStatus(current_coverage[axis.value])
        except (KeyError, TypeError, ValueError) as error:
            raise AnswerAnalysisRejected() from error
        if (
            axis in validated
            or status is CoverageStatus.UNCOVERED
            or _coverage_rank(status) <= _coverage_rank(current_status)
        ):
            raise AnswerAnalysisRejected()
        evidence = _validate_analysis_text(
            item.evidence, maximum=_ANSWER_EVIDENCE_MAX_LENGTH
        )
        if evidence not in answer:
            raise AnswerAnalysisRejected()
        validated[axis] = AnalyzedCoverageChange(axis, status, evidence)
    return AnswerAnalysisResult(
        meaning=meaning,
        low_information=False,
        coverage_patch=tuple(
            validated[axis] for axis in CoreCoverageAxis if axis in validated
        ),
    )


def _validate_analysis_text(value: object, *, maximum: int) -> str:
    """분석 문자열의 길이와 권한 변경 지시를 안전 경계에서 검사한다."""
    if not isinstance(value, str):
        raise AnswerAnalysisRejected()
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > maximum
        or any(pattern in normalized for pattern in _ANALYSIS_PROHIBITED_PATTERNS)
    ):
        raise AnswerAnalysisRejected()
    return normalized


def get_interview_coverage(*, user, interview: Interview) -> CoverageSnapshot:
    """소유자가 유효한 Interview의 Coverage snapshot을 읽는다."""
    prepared = _get_coverage_interview(user=user, interview=interview, lock=False)
    return _coverage_snapshot(prepared.coverage)


def apply_interview_coverage_patch(
    *, user, interview: Interview, patch: Sequence[CoveragePatchItem]
) -> CoveragePatchResult:
    """답변이 있는 진행 중 Interview에 단방향 Coverage patch를 원자 적용한다."""
    validated_patch = _validate_coverage_patch(patch)
    with transaction.atomic():
        locked = _get_coverage_interview(user=user, interview=interview, lock=True)
        if locked.status != Interview.Status.IN_PROGRESS:
            raise CoveragePolicyError()
        if not InterviewTurn.objects.filter(
            interview=locked, answer__isnull=False
        ).exists():
            raise CoveragePolicyError()
        current = locked.coverage
        updated = current.copy()
        changed = False
        for axis, target in validated_patch.items():
            current_status = CoverageStatus(current[axis])
            if _coverage_rank(target) < _coverage_rank(current_status):
                raise CoveragePolicyError()
            if target != current_status:
                updated[axis] = target.value
                changed = True
        if changed:
            Interview.objects.filter(pk=locked.pk).update(
                coverage=updated, updated_at=timezone.now()
            )
        return CoveragePatchResult(
            snapshot=_coverage_snapshot(updated), changed=changed
        )


def _get_coverage_interview(*, user, interview: Interview, lock: bool) -> Interview:
    """소유권, 관계 및 canonical 저장 shape를 공통 검증한다."""
    if not isinstance(interview, Interview) or interview.pk is None:
        raise CoveragePolicyError()
    queryset = Interview.objects.select_related("reading")
    if lock:
        queryset = queryset.select_for_update()
    prepared = queryset.filter(pk=interview.pk, reading__user=user).first()
    if (
        prepared is None
        or prepared.book_id != prepared.reading.book_id
        or not is_canonical_coverage(prepared.coverage)
    ):
        raise CoveragePolicyError()
    return prepared


def _validate_coverage_patch(
    patch: Sequence[CoveragePatchItem],
) -> MappingProxyType:
    """순서 있는 patch의 허용 enum과 축 중복을 DB 접근 전에 검증한다."""
    if not isinstance(patch, Sequence) or isinstance(patch, (str, bytes)):
        raise CoveragePolicyError()
    validated: dict[str, CoverageStatus] = {}
    for item in patch:
        if not isinstance(item, CoveragePatchItem):
            raise CoveragePolicyError()
        try:
            axis = CoreCoverageAxis(item.axis)
            status = CoverageStatus(item.status)
        except (TypeError, ValueError) as error:
            raise CoveragePolicyError() from error
        if axis.value in validated:
            raise CoveragePolicyError()
        validated[axis.value] = status
    return MappingProxyType(validated)


def _coverage_snapshot(coverage: object) -> CoverageSnapshot:
    """검증된 JSON object를 read-only Coverage 값으로 변환한다."""
    if not is_canonical_coverage(coverage):
        raise CoveragePolicyError()
    return CoverageSnapshot(
        memory=CoverageStatus(coverage[CoreCoverageAxis.MEMORY.value]),
        reaction=CoverageStatus(coverage[CoreCoverageAxis.REACTION.value]),
        connection=CoverageStatus(coverage[CoreCoverageAxis.CONNECTION.value]),
        afterthought=CoverageStatus(coverage[CoreCoverageAxis.AFTERTHOUGHT.value]),
    )


def _coverage_rank(status: CoverageStatus) -> int:
    """단방향 전환 비교에만 사용하는 Coverage 상태 순서다."""
    statuses = (
        CoverageStatus.UNCOVERED,
        CoverageStatus.PARTIAL,
        CoverageStatus.COVERED,
    )
    return statuses.index(status)
