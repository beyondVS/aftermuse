from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from django.conf import settings
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from integrations.llm.contracts import (
    AnswerAnalysisProvider,
    AnswerAnalysisRejected,
    CurrentCoverageItem,
    NextQuestionContext,
    NextQuestionProvider,
    PreviousTurn,
    ProposedAnswerAnalysis,
    ProposedCoverageChange,
    ProposedNextQuestion,
    QuestionGenerationRejected,
    QuestionProvider,
)
from knowledge.services import BookKnowledgeReadiness, get_book_knowledge_readiness
from readings.models import Reading
from reflections.models import (
    CoreCoverageAxis,
    CoverageStatus,
    Interview,
    InterviewProgressDecision,
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
_BOOK_FACT_CUES = ("주인공", "등장인물", "결말", "범인", "사건", "작가의 주장")
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
    ENDED_NO_REFLECTION = "ENDED_NO_REFLECTION"


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


class NextTurnPersistenceError(Exception):
    """후속 상태 확정 실패를 답변 보존과 분리한다."""


class NextTurnStaleError(Exception):
    """Provider 호출 중 Interview 상태가 바뀌어 재시도가 필요하다."""


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


@dataclass(frozen=True, slots=True)
class NextTurnResult:
    """확정된 다음 질문 또는 질문 생략 상태다."""

    turn: InterviewTurn
    skipped: bool


@dataclass(frozen=True, slots=True)
class UserSkipResult:
    """사용자의 질문 건너뛰기 결과다."""

    interview: Interview
    skipped_turn: InterviewTurn
    destination: InterviewDestination
    next_turn: InterviewTurn | None = None


@dataclass(frozen=True, slots=True)
class InterviewBudget:
    """미답변 질문과 완료 답변, 사용자 건너뛰기를 구분한 현재 Interview의 질문 수다."""

    question_count: int
    answered_count: int
    user_skipped_count: int = 0

    @property
    def resolved_count(self) -> int:
        return self.answered_count + self.user_skipped_count


def _all_covered(coverage: dict[str, str]) -> bool:
    """네 Core 방향이 모두 충분히 다뤄졌는지 판정한다."""
    return all(value == CoverageStatus.COVERED for value in coverage.values())


def _has_uncovered(coverage: dict[str, str]) -> bool:
    """일반 상한 예외를 고려할 미탐색 방향이 있는지 판정한다."""
    return CoverageStatus.UNCOVERED in coverage.values()


def _validated_budget(interview: Interview, turn: InterviewTurn) -> InterviewBudget:
    """현재 마지막 Turn이 연속된 해결(답변 또는 사용자 건너뛰기)인지
    확인하고 실제 행 수를 반환한다."""
    counts = InterviewTurn.objects.filter(interview=interview).aggregate(
        question_count=Count("id"),
        answered_count=Count("id", filter=Q(answer__isnull=False)),
        user_skipped_count=Count("id", filter=Q(user_skipped_at__isnull=False)),
    )
    budget = InterviewBudget(**counts)
    if (
        budget.question_count != turn.sequence
        or budget.resolved_count != budget.question_count
    ):
        raise InterviewPolicyError()
    return budget


def _budget_action(budget: InterviewBudget, coverage: dict[str, str]) -> str:
    """답변 수에 따른 우선순위를 적용하며 목표 범위는 종료 조건으로 쓰지 않는다."""
    if budget.question_count >= settings.INTERVIEW_QUESTION_ABSOLUTE_CAP:
        return "ready"
    if budget.answered_count >= settings.INTERVIEW_QUESTION_NORMAL_CAP:
        return "cap" if _has_uncovered(coverage) else "ready"
    if budget.answered_count >= 4 and _all_covered(coverage):
        return "soft"
    return "normal"


def get_interview_destination(interview: Interview) -> InterviewDestination:
    """현재 Interview 상태를 후속 화면 목적지로 변환한다."""
    destinations = {
        Interview.Status.IN_PROGRESS: InterviewDestination.INTERVIEW,
        Interview.Status.REFLECTION_READY: InterviewDestination.REFLECTION_READY,
        Interview.Status.COMPLETED: InterviewDestination.REFLECTION_COMPLETED,
        Interview.Status.ENDED_NO_REFLECTION: InterviewDestination.ENDED_NO_REFLECTION,
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
    """저장 전 질문의 줄 수, 길이, 문장 종결 조건을 검증한다."""
    if not isinstance(question, str):
        raise QuestionGenerationRejected()
    normalized = question.strip()
    if (
        not normalized
        or len(normalized) > 300
        or "\n" in normalized
        or not normalized.endswith(("?", "？"))
        or any(pattern in normalized for pattern in _QUESTION_PROHIBITED_PATTERNS)
    ):
        raise QuestionGenerationRejected()
    return normalized


def save_first_answer(
    *, user, interview: Interview, answer: object
) -> FirstAnswerSaveResult:
    """첫 답변을 한 번만 확정하고 같은 재제출은 멱등 처리한다."""
    return save_turn_answer(user=user, interview=interview, sequence=1, answer=answer)


def _validate_save_turn_args(interview: Interview, sequence: int) -> None:
    """답변 저장 대상 인터뷰 및 sequence 기본 인자를 검증한다."""
    if not isinstance(interview, Interview) or interview.pk is None:
        raise InterviewPolicyError()
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise InterviewPolicyError()


def save_turn_answer(
    *, user, interview: Interview, sequence: int, answer: object
) -> FirstAnswerSaveResult:
    """현재 마지막 Turn의 답변을 먼저 확정하고 재제출을 멱등 처리한다."""
    validated_answer = _validate_first_answer(answer)
    _validate_save_turn_args(interview, sequence)
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
                .filter(interview=locked_interview, sequence=sequence)
                .first()
            )
            if turn is None:
                raise InterviewPolicyError()
            if turn.user_skipped_at is not None:
                raise InterviewPolicyError()
            if turn.answer is not None:
                if turn.answer == validated_answer:
                    return FirstAnswerSaveResult(turn=turn, saved=False)
                raise FirstAnswerConflict(turn)
            latest = InterviewTurn.objects.filter(interview=locked_interview).last()
            if latest is None or latest.pk != turn.pk:
                raise InterviewPolicyError()
            turn.answer = validated_answer
            turn.full_clean()
            turn.save(update_fields=("answer", "updated_at"))
            return FirstAnswerSaveResult(turn=turn, saved=True)
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


def process_next_turn(  # noqa: C901
    *,
    user,
    interview: Interview,
    turn: InterviewTurn,
    analysis_provider: AnswerAnalysisProvider | None = None,
    next_provider: NextQuestionProvider | None = None,
) -> NextTurnResult:
    """확정 답변 뒤 검증된 Coverage와 다음 Turn 또는 생략을 함께 확정한다."""
    if not isinstance(interview, Interview) or interview.pk is None:
        raise AnswerAnalysisPolicyError()
    persisted = Interview.objects.filter(pk=interview.pk, reading__user=user).first()
    if persisted is None:
        raise AnswerAnalysisPolicyError()
    if persisted.status == Interview.Status.REFLECTION_READY:
        latest = InterviewTurn.objects.filter(interview=persisted).last()
        if latest is not None and latest.pk == turn.pk and latest.answer is not None:
            return NextTurnResult(latest, skipped=True)
        raise InterviewPolicyError()
    prepared, answered = _get_answer_analysis_target(
        user=user, interview=interview, turn=turn
    )
    existing = InterviewTurn.objects.filter(
        interview=prepared, sequence=answered.sequence + 1
    ).first()
    if existing is not None:
        return NextTurnResult(existing, skipped=False)
    if answered.next_question_skipped_at is not None:
        return _commit_legacy_skip(user=user, interview=prepared, answered=answered)
    if InterviewProgressDecision.objects.filter(turn=answered).exists():
        return NextTurnResult(answered, skipped=False)
    if InterviewTurn.objects.filter(
        interview=prepared, sequence__gt=answered.sequence
    ).exists():
        raise InterviewPolicyError()
    budget = _validated_budget(prepared, answered)
    before = prepared.coverage.copy()
    analysis = analyze_interview_answer(
        user=user, interview=prepared, turn=answered, provider=analysis_provider
    )
    projected = before.copy()
    for change in analysis.coverage_patch:
        projected[change.axis.value] = change.status.value

    action = _budget_action(budget, projected)
    if (
        action == "cap"
        and budget.answered_count > settings.INTERVIEW_QUESTION_NORMAL_CAP
    ):
        granted = InterviewProgressDecision.objects.filter(
            turn__interview=prepared,
            turn__sequence=settings.INTERVIEW_QUESTION_NORMAL_CAP,
            kind=InterviewProgressDecision.Kind.CAP_EXTENSION,
            selection=InterviewProgressDecision.Selection.CONTINUE,
        ).exists()
        if not granted:
            raise InterviewPolicyError()
        action = "extended"
    if action == "ready":
        return _commit_next_turn(
            user=user,
            prepared=prepared,
            answered=answered,
            before=before,
            projected=projected,
            question=None,
            action=action,
            budget_before=budget,
            candidate_focus_axis=None,
        )

    from reflections.context import build_interview_question_context

    question_context = build_interview_question_context(interview=prepared)
    history = tuple(
        PreviousTurn(question=item.question, answer=item.answer)
        for item in InterviewTurn.objects.filter(
            interview=prepared, sequence__lt=answered.sequence, answer__isnull=False
        ).order_by("-sequence")[:5]
    )
    context = NextQuestionContext(
        question_context=question_context,
        previous_turns=tuple(reversed(history)),
        question=answered.question,
        answer=answered.answer,
        meaning=analysis.meaning,
        low_information=analysis.low_information,
        coverage=tuple(
            CurrentCoverageItem(axis=axis.value, status=projected[axis.value])
            for axis in CoreCoverageAxis
        ),
        budget_mode="CAP_EXTENSION" if action in ("cap", "extended") else "NORMAL",
    )
    if next_provider is None:
        from integrations.llm.factory import get_next_question_provider

        next_provider = get_next_question_provider()
    proposal = next_provider.generate_next_question(context)
    question = _validate_next_question(proposal, context)
    candidate_focus_axis = (
        CoreCoverageAxis(proposal.focus_axis) if question is not None else None
    )
    if action in ("cap", "extended") and question is not None:
        if (
            proposal.focus_axis
            not in (
                axis
                for axis, status in projected.items()
                if status == CoverageStatus.UNCOVERED
            )
            or proposal.grounding_quote is None
        ):
            raise QuestionGenerationRejected()
    return _commit_next_turn(
        user=user,
        prepared=prepared,
        answered=answered,
        before=before,
        projected=projected,
        question=question,
        action=action,
        budget_before=budget,
        candidate_focus_axis=candidate_focus_axis,
    )


def _commit_legacy_skip(
    *, user, interview: Interview, answered: InterviewTurn
) -> NextTurnResult:
    """Day 07 생략 표식을 재분석 없이 준비 상태로 확정한다."""
    try:
        with transaction.atomic():
            locked = (
                Interview.objects.select_for_update()
                .filter(pk=interview.pk, reading__user=user)
                .first()
            )
            if locked is None:
                raise InterviewPolicyError()
            current = InterviewTurn.objects.select_for_update().get(pk=answered.pk)
            if (
                current.interview_id != locked.pk
                or current.next_question_skipped_at is None
            ):
                raise InterviewPolicyError()
            if locked.status == Interview.Status.IN_PROGRESS:
                locked.status = Interview.Status.REFLECTION_READY
                locked.save(update_fields=("status", "updated_at"))
            elif locked.status != Interview.Status.REFLECTION_READY:
                raise InterviewPolicyError()
            return NextTurnResult(current, skipped=True)
    except DatabaseError as error:
        raise NextTurnPersistenceError() from error


def decide_interview_progress(  # noqa: C901
    *, user, interview: Interview, sequence: int, decision: str
) -> NextTurnResult:
    """보류 질문의 종료·계속 선택을 Interview 잠금 아래 한 번만 확정한다."""
    if (
        not isinstance(interview, Interview)
        or interview.pk is None
        or not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence < 1
        or decision not in ("end", "continue")
    ):
        raise InterviewPolicyError()
    selection = (
        InterviewProgressDecision.Selection.END
        if decision == "end"
        else InterviewProgressDecision.Selection.CONTINUE
    )
    try:
        with transaction.atomic():
            locked = (
                Interview.objects.select_for_update()
                .filter(pk=interview.pk, reading__user=user)
                .first()
            )
            if locked is None:
                raise InterviewPolicyError()
            turn = (
                InterviewTurn.objects.select_for_update()
                .filter(interview=locked, sequence=sequence)
                .filter(Q(answer__isnull=False) | Q(user_skipped_at__isnull=False))
                .first()
            )
            if turn is None:
                raise InterviewPolicyError()
            choice = (
                InterviewProgressDecision.objects.select_for_update()
                .filter(turn=turn)
                .first()
            )
            if choice is None:
                raise InterviewPolicyError()
            if choice.selection is not None:
                if choice.selection != selection:
                    raise InterviewPolicyError()
                if selection == InterviewProgressDecision.Selection.END:
                    return NextTurnResult(turn, skipped=True)
                existing = InterviewTurn.objects.filter(
                    interview=locked, sequence=sequence + 1
                ).first()
                if existing is None:
                    raise InterviewPolicyError()
                return NextTurnResult(existing, skipped=False)
            if (
                locked.status != Interview.Status.IN_PROGRESS
                or (InterviewTurn.objects.filter(interview=locked).last().pk != turn.pk)
                or sequence >= settings.INTERVIEW_QUESTION_ABSOLUTE_CAP
            ):
                raise InterviewPolicyError()
            if (
                choice.kind == InterviewProgressDecision.Kind.CAP_EXTENSION
                and sequence != settings.INTERVIEW_QUESTION_NORMAL_CAP
            ):
                raise InterviewPolicyError()
            if selection == InterviewProgressDecision.Selection.CONTINUE:
                budget = _validated_budget(locked, turn)
                if budget.question_count >= settings.INTERVIEW_QUESTION_ABSOLUTE_CAP:
                    raise InterviewPolicyError()
                if choice.kind == InterviewProgressDecision.Kind.CAP_EXTENSION and (
                    choice.candidate_focus_axis is None
                    or locked.coverage.get(choice.candidate_focus_axis)
                    != CoverageStatus.UNCOVERED
                ):
                    raise InterviewPolicyError()
            choice.selection = selection
            choice.decided_at = timezone.now()
            choice.save(update_fields=("selection", "decided_at"))
            if selection == InterviewProgressDecision.Selection.END:
                locked.status = Interview.Status.REFLECTION_READY
                locked.save(update_fields=("status", "updated_at"))
                return NextTurnResult(turn, skipped=True)
            created = InterviewTurn.objects.create(
                interview=locked,
                sequence=sequence + 1,
                question=choice.candidate_question,
            )
            return NextTurnResult(created, skipped=False)
    except DatabaseError as error:
        raise NextTurnPersistenceError() from error


def _commit_next_turn(  # noqa: C901
    *,
    user,
    prepared: Interview,
    answered: InterviewTurn,
    before: dict[str, str],
    projected: dict[str, str],
    question: str | None,
    action: str = "normal",
    budget_before: InterviewBudget | None = None,
    candidate_focus_axis: CoreCoverageAxis | None = None,
) -> NextTurnResult:
    """Provider 호출 뒤 상태 재검증과 영속 변경을 짧은 잠금으로 묶는다."""
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
            current = InterviewTurn.objects.select_for_update().get(pk=answered.pk)
            if (
                current.interview_id != locked.pk
                or current.answer != answered.answer
                or current.user_skipped_at is not None
            ):
                raise NextTurnStaleError()
            existing = InterviewTurn.objects.filter(
                interview=locked, sequence=current.sequence + 1
            ).first()
            if existing is not None:
                return NextTurnResult(existing, skipped=False)
            if current.next_question_skipped_at is not None:
                return NextTurnResult(current, skipped=True)
            if InterviewProgressDecision.objects.filter(turn=current).exists():
                return NextTurnResult(current, skipped=False)
            if locked.status == Interview.Status.REFLECTION_READY and (
                InterviewTurn.objects.filter(interview=locked).last().pk == current.pk
            ):
                return NextTurnResult(current, skipped=True)
            _validate_interview_state(locked)
            budget = _validated_budget(locked, current)
            if budget_before is not None and budget != budget_before:
                raise NextTurnStaleError()
            if locked.coverage != before:
                raise NextTurnStaleError()
            if projected != before:
                Interview.objects.filter(pk=locked.pk).update(
                    coverage=projected, updated_at=timezone.now()
                )
            if question is None:
                if action != "ready":
                    current.next_question_skipped_at = timezone.now()
                    current.save(
                        update_fields=("next_question_skipped_at", "updated_at")
                    )
                locked.status = Interview.Status.REFLECTION_READY
                locked.save(update_fields=("status", "updated_at"))
                return NextTurnResult(current, skipped=True)
            if action in ("soft", "cap"):
                if action == "cap" and (
                    candidate_focus_axis is None
                    or projected[candidate_focus_axis.value] != CoverageStatus.UNCOVERED
                ):
                    raise NextTurnStaleError()
                InterviewProgressDecision.objects.create(
                    turn=current,
                    kind=(
                        InterviewProgressDecision.Kind.SOFT_STOP
                        if action == "soft"
                        else InterviewProgressDecision.Kind.CAP_EXTENSION
                    ),
                    candidate_question=question,
                    candidate_focus_axis=candidate_focus_axis,
                )
                return NextTurnResult(current, skipped=False)
            if budget.question_count >= settings.INTERVIEW_QUESTION_ABSOLUTE_CAP:
                raise InterviewPolicyError()
            created = InterviewTurn.objects.create(
                interview=locked, sequence=current.sequence + 1, question=question
            )
            return NextTurnResult(created, skipped=False)
    except DatabaseError as error:
        raise NextTurnPersistenceError() from error


def skip_interview_turn(  # noqa: C901
    *,
    user,
    interview: Interview,
    sequence: int,
    next_provider: NextQuestionProvider | None = None,
) -> UserSkipResult:
    """현재 마지막 질문을 건너뛰고 답변 없이 다음 질문 또는 종료 상태로 전이한다."""
    if not isinstance(interview, Interview) or interview.pk is None:
        raise InterviewPolicyError()
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise InterviewPolicyError()

    # 1. 짧은 atomic: skip 선저장 및 budget 판정
    with transaction.atomic():
        locked = (
            Interview.objects.select_for_update()
            .select_related("reading", "book")
            .filter(pk=interview.pk, reading__user=user)
            .first()
        )
        if locked is None:
            raise InterviewPolicyError()
        if locked.book_id != locked.reading.book_id:
            raise InterviewPolicyError()

        turn = (
            InterviewTurn.objects.select_for_update()
            .filter(interview=locked, sequence=sequence)
            .first()
        )
        if turn is None:
            raise InterviewPolicyError()
        if turn.answer is not None:
            raise InterviewPolicyError()

        # 이미 건너뛴 경우 멱등 처리 또는 재개
        if turn.user_skipped_at is None:
            if locked.status != Interview.Status.IN_PROGRESS:
                raise InterviewPolicyError()
            latest = (
                InterviewTurn.objects.filter(interview=locked)
                .order_by("sequence")
                .last()
            )
            if latest is None or latest.pk != turn.pk or turn.sequence != sequence:
                raise InterviewPolicyError()
            turn.user_skipped_at = timezone.now()
            turn.save(update_fields=("user_skipped_at", "updated_at"))

        # 인터뷰가 이미 종결 상태인 경우 안전하게 수렴
        if locked.status != Interview.Status.IN_PROGRESS:
            return UserSkipResult(
                interview=locked,
                skipped_turn=turn,
                destination=get_interview_destination(locked),
                next_turn=None,
            )

        latest = (
            InterviewTurn.objects.filter(interview=locked).order_by("sequence").last()
        )
        if latest is None:
            raise InterviewPolicyError()

        # 이미 후속 Turn으로 진행된 stale Skip replay인 경우 현재 최신 Turn으로 수렴
        if latest.sequence > turn.sequence:
            return UserSkipResult(
                interview=locked,
                skipped_turn=turn,
                destination=InterviewDestination.INTERVIEW,
                next_turn=latest,
            )

        existing_decision = InterviewProgressDecision.objects.filter(turn=turn).first()
        if existing_decision is not None:
            if existing_decision.selection == InterviewProgressDecision.Selection.END:
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=turn,
                    destination=get_interview_destination(locked),
                    next_turn=None,
                )
            if (
                existing_decision.selection
                == InterviewProgressDecision.Selection.CONTINUE
            ):
                next_after_decision = InterviewTurn.objects.filter(
                    interview=locked, sequence=turn.sequence + 1
                ).first()
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=turn,
                    destination=InterviewDestination.INTERVIEW,
                    next_turn=next_after_decision or latest,
                )
            return UserSkipResult(
                interview=locked,
                skipped_turn=turn,
                destination=InterviewDestination.INTERVIEW,
                next_turn=None,
            )

        if latest.pk != turn.pk or turn.sequence != sequence:
            raise InterviewPolicyError()

        budget = _validated_budget(locked, turn)

        # 종결 또는 다음 질문 필요 여부 판정
        if budget.resolved_count >= settings.INTERVIEW_QUESTION_ABSOLUTE_CAP:
            locked.status = (
                Interview.Status.REFLECTION_READY
                if budget.answered_count > 0
                else Interview.Status.ENDED_NO_REFLECTION
            )
            locked.save(update_fields=("status", "updated_at"))
            return UserSkipResult(
                interview=locked,
                skipped_turn=turn,
                destination=get_interview_destination(locked),
                next_turn=None,
            )

        if budget.resolved_count >= settings.INTERVIEW_QUESTION_NORMAL_CAP:
            if budget.answered_count == 0:
                locked.status = Interview.Status.ENDED_NO_REFLECTION
                locked.save(update_fields=("status", "updated_at"))
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=turn,
                    destination=InterviewDestination.ENDED_NO_REFLECTION,
                    next_turn=None,
                )
            action = "cap" if _has_uncovered(locked.coverage) else "ready"
            if action == "ready":
                locked.status = Interview.Status.REFLECTION_READY
                locked.save(update_fields=("status", "updated_at"))
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=turn,
                    destination=InterviewDestination.REFLECTION_READY,
                    next_turn=None,
                )
        else:
            action = (
                "soft"
                if (budget.answered_count >= 4 and _all_covered(locked.coverage))
                else "normal"
            )

        prepared_interview = locked
        prepared_turn = turn
        prepared_coverage = locked.coverage.copy()

    # 2. Transaction 밖: 다음 질문 provider 호출
    from reflections.context import build_interview_question_context

    question_context = build_interview_question_context(interview=prepared_interview)
    history = tuple(
        PreviousTurn(question=item.question, answer=item.answer)
        for item in InterviewTurn.objects.filter(
            interview=prepared_interview,
            sequence__lt=prepared_turn.sequence,
            answer__isnull=False,
        ).order_by("-sequence")[:5]
    )
    skipped_questions = tuple(
        InterviewTurn.objects.filter(
            interview=prepared_interview,
            sequence__lte=prepared_turn.sequence,
            user_skipped_at__isnull=False,
        )
        .order_by("sequence")
        .values_list("question", flat=True)
    )
    context = NextQuestionContext(
        question_context=question_context,
        previous_turns=tuple(reversed(history)),
        question=prepared_turn.question,
        answer=None,
        meaning=None,
        low_information=False,
        coverage=tuple(
            CurrentCoverageItem(axis=axis.value, status=prepared_coverage[axis.value])
            for axis in CoreCoverageAxis
        ),
        budget_mode="CAP_EXTENSION" if action in ("cap", "extended") else "NORMAL",
        user_skipped=True,
        skipped_questions=skipped_questions,
    )
    if next_provider is None:
        from integrations.llm.factory import get_next_question_provider

        next_provider = get_next_question_provider()

    proposal = next_provider.generate_next_question(context)
    question = _validate_next_question(proposal, context)
    candidate_focus_axis = (
        CoreCoverageAxis(proposal.focus_axis)
        if question is not None and proposal.focus_axis
        else None
    )
    if action in ("cap", "extended") and question is not None:
        if (
            proposal.focus_axis
            not in (
                axis
                for axis, status in prepared_coverage.items()
                if status == CoverageStatus.UNCOVERED
            )
            or proposal.grounding_quote is None
        ):
            raise QuestionGenerationRejected()

    # 3. 두 번째 짧은 atomic: 재검증 후 다음 Turn 또는 Decision 확정
    try:
        with transaction.atomic():
            locked = (
                Interview.objects.select_for_update()
                .select_related("reading", "book")
                .filter(pk=prepared_interview.pk, reading__user=user)
                .first()
            )
            if locked is None:
                raise InterviewPolicyError()
            current = InterviewTurn.objects.select_for_update().get(pk=prepared_turn.pk)
            if current.interview_id != locked.pk or current.user_skipped_at is None:
                raise NextTurnStaleError()

            existing_next = InterviewTurn.objects.filter(
                interview=locked, sequence=current.sequence + 1
            ).first()
            if existing_next is not None:
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=current,
                    destination=InterviewDestination.INTERVIEW,
                    next_turn=existing_next,
                )

            if InterviewProgressDecision.objects.filter(turn=current).exists():
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=current,
                    destination=InterviewDestination.INTERVIEW,
                    next_turn=None,
                )

            if locked.status in (
                Interview.Status.REFLECTION_READY,
                Interview.Status.ENDED_NO_REFLECTION,
            ):
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=current,
                    destination=get_interview_destination(locked),
                    next_turn=None,
                )

            budget_now = _validated_budget(locked, current)
            if budget_now != budget:
                raise NextTurnStaleError()
            if locked.coverage != prepared_coverage:
                raise NextTurnStaleError()

            if question is None:
                locked.status = (
                    Interview.Status.REFLECTION_READY
                    if budget_now.answered_count > 0
                    else Interview.Status.ENDED_NO_REFLECTION
                )
                locked.save(update_fields=("status", "updated_at"))
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=current,
                    destination=get_interview_destination(locked),
                    next_turn=None,
                )

            if action in ("soft", "cap"):
                if action == "cap" and (
                    candidate_focus_axis is None
                    or prepared_coverage[candidate_focus_axis.value]
                    != CoverageStatus.UNCOVERED
                ):
                    raise NextTurnStaleError()
                InterviewProgressDecision.objects.create(
                    turn=current,
                    kind=(
                        InterviewProgressDecision.Kind.SOFT_STOP
                        if action == "soft"
                        else InterviewProgressDecision.Kind.CAP_EXTENSION
                    ),
                    candidate_question=question,
                    candidate_focus_axis=candidate_focus_axis,
                )
                return UserSkipResult(
                    interview=locked,
                    skipped_turn=current,
                    destination=InterviewDestination.INTERVIEW,
                    next_turn=None,
                )

            created = InterviewTurn.objects.create(
                interview=locked,
                sequence=current.sequence + 1,
                question=question,
            )
            return UserSkipResult(
                interview=locked,
                skipped_turn=current,
                destination=InterviewDestination.INTERVIEW,
                next_turn=created,
            )
    except DatabaseError as error:
        raise NextTurnPersistenceError() from error


def _validate_next_question(
    proposal: object, context: NextQuestionContext
) -> str | None:
    """질문·생략 제안을 전체 검증하고 실행 가능한 결과로 변환한다."""
    if not isinstance(proposal, ProposedNextQuestion):
        raise QuestionGenerationRejected()
    if proposal.kind == "skip":
        _validate_skip_proposal(proposal, context)
        return None
    if proposal.kind != "question" or proposal.skip_reason is not None:
        raise QuestionGenerationRejected()
    try:
        axis = CoreCoverageAxis(proposal.focus_axis)
    except (TypeError, ValueError) as error:
        raise QuestionGenerationRejected() from error
    question = _validate_first_question(proposal.question)
    if context.question_context.knowledge_readiness == "READY_LIMITED":
        _validate_ready_limited_grounding(question, context)
    if proposal.grounding_quote is not None:
        if (
            not isinstance(proposal.grounding_quote, str)
            or not 1 <= len(proposal.grounding_quote.strip()) <= 500
            or not _is_confirmed_grounding(proposal.grounding_quote.strip(), context)
            or not _question_uses_grounding(question, proposal.grounding_quote.strip())
        ):
            raise QuestionGenerationRejected()
    elif (not context.low_information and not context.user_skipped) or next(
        item.status for item in context.coverage if item.axis == axis.value
    ) == CoverageStatus.COVERED:
        raise QuestionGenerationRejected()
    return question


def _validate_ready_limited_grounding(
    question: str, context: NextQuestionContext
) -> None:
    """READY_LIMITED에서 확인되지 않은 책 사실 전제를 차단한다."""
    answers = [item.answer for item in context.previous_turns if item.answer]
    if context.answer:
        answers.append(context.answer)
    confirmed = " ".join(answers)
    if any(cue in question and cue not in confirmed for cue in _BOOK_FACT_CUES):
        raise QuestionGenerationRejected()


def _is_confirmed_grounding(quote: str, context: NextQuestionContext) -> bool:
    """질문 근거를 확정된 사용자 발화나 검증된 Claim으로 제한한다."""
    sources = [item.answer for item in context.previous_turns if item.answer]
    if context.answer:
        sources.append(context.answer)
    if context.question_context.knowledge_readiness == "READY":
        sources.extend(context.question_context.knowledge_claims)
    return any(quote in source for source in sources)


def _question_uses_grounding(question: str, quote: str) -> bool:
    """제안 근거와 질문 문구의 기계적으로 확인 가능한 연결을 요구한다."""
    normalized = " ".join(quote.split())
    if normalized in question:
        return True
    significant = [word for word in normalized.split() if len(word) >= 3]
    return any(word in question for word in significant)


def _validate_skip_proposal(
    proposal: ProposedNextQuestion, context: NextQuestionContext
) -> None:
    """생략은 네 축 완료와 구체적인 추가 탐색 없음 제안을 함께 요구한다."""
    if (
        proposal.question is not None
        or proposal.focus_axis is not None
        or proposal.grounding_quote is not None
        or (
            context.budget_mode != "CAP_EXTENSION"
            and any(item.status != CoverageStatus.COVERED for item in context.coverage)
        )
        or not isinstance(proposal.skip_reason, str)
        or not 10 <= len(proposal.skip_reason.strip()) <= 500
        or any(
            pattern in proposal.skip_reason for pattern in _QUESTION_PROHIBITED_PATTERNS
        )
    ):
        raise QuestionGenerationRejected()


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
        _validate_analysis_coverage_transition(axis, status, current_status, validated)
        evidence = _validate_analysis_text(
            item.evidence, maximum=_ANSWER_EVIDENCE_MAX_LENGTH
        )
        if evidence not in answer:
            raise AnswerAnalysisRejected(reason_code="analysis_evidence_not_verbatim")
        validated[axis] = AnalyzedCoverageChange(axis, status, evidence)
    return AnswerAnalysisResult(
        meaning=meaning,
        low_information=False,
        coverage_patch=tuple(
            validated[axis] for axis in CoreCoverageAxis if axis in validated
        ),
    )


def _validate_analysis_coverage_transition(axis, status, current_status, validated):
    """단방향 Coverage 계약의 위반 조건을 원문 없는 코드로 구별한다."""
    if axis in validated:
        raise AnswerAnalysisRejected(reason_code="analysis_duplicate_axis")
    if status is CoverageStatus.UNCOVERED:
        raise AnswerAnalysisRejected(reason_code="analysis_uncovered_status")
    if _coverage_rank(status) <= _coverage_rank(current_status):
        raise AnswerAnalysisRejected(reason_code="analysis_non_increasing_coverage")


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
