import logging
import traceback

from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from integrations.llm.contracts import AnswerAnalysisError, QuestionGenerationError
from integrations.llm.factory import get_question_provider
from knowledge.services import get_book_knowledge_readiness
from readings.models import Reading
from reflections.drafts import generate_or_get_reflection_draft
from reflections.forms import FirstAnswerForm
from reflections.models import (
    Interview,
    InterviewProgressDecision,
    InterviewTurn,
    Reflection,
)
from reflections.services import (
    AnswerAnalysisPolicyError,
    FirstAnswerConflict,
    FirstAnswerPersistenceError,
    InterviewDestination,
    InterviewPolicyError,
    NextTurnPersistenceError,
    NextTurnStaleError,
    decide_interview_progress,
    ensure_first_question,
    get_interview_destination,
    process_next_turn,
    save_first_answer,
    save_turn_answer,
    skip_interview_turn,
    start_interview,
)

logger = logging.getLogger(__name__)

_ANALYSIS_FAILURE_REASONS = {
    "analysis_invalid_output": (
        "답변 분석 결과의 형식 또는 내용이 검증 기준을 만족하지 못했습니다."
    ),
    "analysis_duplicate_axis": "답변 분석이 같은 Coverage 축을 중복 제안했습니다.",
    "analysis_uncovered_status": (
        "답변 분석이 허용되지 않는 UNCOVERED 상태를 제안했습니다."
    ),
    "analysis_non_increasing_coverage": (
        "답변 분석이 이미 반영된 상태와 같거나 낮은 Coverage 상태를 제안했습니다."
    ),
    "analysis_evidence_not_verbatim": (
        "답변 분석의 근거 인용이 저장된 답변 원문과 일치하지 않습니다."
    ),
}


def _pipeline_failure_details(error: Exception) -> dict[str, str]:
    """고정된 코드와 설명만 응답에 제공하고 예외 원문은 노출하지 않는다."""
    error_type = type(error).__name__
    code = getattr(error, "reason_code", None)
    if error_type == "AnswerAnalysisRejected":
        code = code if code in _ANALYSIS_FAILURE_REASONS else "analysis_invalid_output"
        reason = _ANALYSIS_FAILURE_REASONS[code]
    else:
        code = error_type
        if error_type.endswith("Timeout"):
            reason = "AI 서비스의 응답 대기 시간이 초과되었습니다."
        elif error_type.endswith("ConfigurationError"):
            reason = "AI 서비스 연결 설정을 확인해야 합니다."
        elif error_type.endswith("Unavailable"):
            reason = "AI 서비스 요청이 연결 또는 서비스 오류로 실패했습니다."
        elif error_type == "QuestionGenerationRejected":
            reason = (
                "생성된 질문이 질문 형식·근거·생략 정책 검증을 통과하지 못했습니다."
            )
        elif error_type in (
            "ReflectionGenerationRejected",
            "ReflectionValidationError",
        ):
            reason = (
                "독서노트 초안을 구성하는 중 일시적인 문제가 발생했습니다. "
                "다시 시도해 주세요."
            )
        elif error_type == "NextTurnStaleError":
            reason = (
                "처리 중 Interview 상태가 변경되었습니다. 화면을 새로고침해 주세요."
            )
        else:
            reason = "질문 처리 결과를 저장하지 못했습니다."
    return {"pipeline_error_code": code, "pipeline_error_reason": reason}


def _log_pipeline_failure(
    stage: str, interview_id: int, sequence: int, error: Exception
):
    """예외 메시지·locals 없이 타입과 코드 위치만 기록해 원문 유출을 막는다."""
    chain = []
    reason_code = _pipeline_failure_details(error)["pipeline_error_code"]
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        frames = traceback.extract_tb(error.__traceback__)
        origin = frames[-1] if frames else None
        chain.append(
            f"{type(error).__name__}@{origin.name}:{origin.lineno}"
            if origin is not None
            else type(error).__name__
        )
        status = getattr(error, "code", None)
        if isinstance(status, int) and 100 <= status <= 599:
            chain[-1] += f"[status={status}]"
        error = error.__cause__ or (
            error.__context__ if not error.__suppress_context__ else None
        )
    logger.warning(
        "Interview pipeline failed stage=%s interview_id=%s sequence=%s "
        "chain=%s reason=%s",
        stage,
        interview_id,
        sequence,
        " -> ".join(chain),
        reason_code,
    )


@require_GET
@login_required
def interview_start(request: HttpRequest, reading_id: int) -> HttpResponse:
    """완독 Reading의 시작 확인 화면 또는 기존 Interview 목적지를 제공한다."""
    reading = get_object_or_404(
        Reading.objects.select_related("book"), pk=reading_id, user=request.user
    )
    existing = Interview.objects.filter(reading=reading).first()
    if existing is not None:
        return _destination_response(request, existing)
    if reading.status != Reading.Status.COMPLETED or reading.completed_on is None:
        return render(
            request,
            "reflections/interview_start.html",
            {
                "reading": reading,
                "error": "완독한 Reading에서만 인터뷰를 시작할 수 있습니다.",
                "can_start": False,
            },
            status=400,
        )
    readiness = get_book_knowledge_readiness(reading.book)
    return render(
        request,
        "reflections/interview_start.html",
        {"reading": reading, "readiness": readiness, "can_start": True},
    )


@require_POST
@login_required
def interview_create(request: HttpRequest, reading_id: int) -> HttpResponse:
    """명시적 POST에서만 Interview를 생성하고 현재 목적지로 이동한다."""
    reading = get_object_or_404(
        Reading.objects.select_related("book"), pk=reading_id, user=request.user
    )
    try:
        result = start_interview(user=request.user, reading=reading)
    except InterviewPolicyError:
        readiness = get_book_knowledge_readiness(reading.book)
        return render(
            request,
            "reflections/interview_start.html",
            {
                "reading": reading,
                "readiness": readiness,
                "error": "인터뷰를 시작할 수 없습니다. 완독 상태를 다시 확인해 주세요.",
                "can_start": False,
            },
            status=400,
        )
    except DatabaseError:
        readiness = get_book_knowledge_readiness(reading.book)
        return render(
            request,
            "reflections/interview_start.html",
            {
                "reading": reading,
                "readiness": readiness,
                "error": "잠시 후 다시 시도해 주세요.",
                "can_start": True,
            },
            status=400,
        )
    return _destination_response(request, result.interview)


@require_GET
@login_required
def interview_detail(request: HttpRequest, interview_id: int) -> HttpResponse:
    """소유자만 진행 중 Interview의 Turn 0개 상태를 볼 수 있게 한다."""
    interview = get_object_or_404(
        Interview.objects.select_related("reading", "book"),
        pk=interview_id,
        reading__user=request.user,
    )
    return _destination_response(request, interview, detail=True)


@require_POST
@login_required
def first_question(request: HttpRequest, interview_id: int) -> HttpResponse:
    """첫 질문 준비 POST를 일반 redirect 또는 HTMX fragment로 반환한다."""
    interview = get_object_or_404(
        Interview.objects.select_related("reading", "book"),
        pk=interview_id,
        reading__user=request.user,
    )
    try:
        turn = ensure_first_question(
            user=request.user,
            interview=interview,
            provider_factory=get_question_provider,
        )
    except InterviewPolicyError:
        return _policy_conflict_response(request)
    except QuestionGenerationError as error:
        _log_pipeline_failure("first", interview.pk, 1, error)
        return _question_error_response(request, interview, error)
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "reflections/_interview_question.html",
            {
                "interview": interview,
                "turn": turn,
                "answer_form": FirstAnswerForm(),
            },
        )
    return redirect("reflections:interview_detail", interview_id=interview.pk)


@require_POST
@login_required
def first_answer(request: HttpRequest, interview_id: int) -> HttpResponse:
    """첫 답변을 확정하고 성공 상태 또는 보존된 입력 오류를 반환한다."""
    return _answer_for_sequence(request, interview_id, sequence=1)


@require_POST
@login_required
def turn_answer(request: HttpRequest, interview_id: int, sequence: int) -> HttpResponse:
    """현재 Turn의 답변을 원문 그대로 확정한다."""
    return _answer_for_sequence(request, interview_id, sequence=sequence)


def _answer_for_sequence(
    request: HttpRequest, interview_id: int, *, sequence: int
) -> HttpResponse:
    interview = get_object_or_404(
        Interview.objects.select_related("reading", "book"),
        pk=interview_id,
        reading__user=request.user,
    )
    turn = get_object_or_404(interview.turns, sequence=sequence)
    form = FirstAnswerForm(request.POST)
    if not form.is_valid():
        return _question_response(request, interview, turn, form, status=400)
    try:
        save = save_first_answer if sequence == 1 else save_turn_answer
        kwargs = {
            "user": request.user,
            "interview": interview,
            "answer": form.cleaned_data["answer"],
        }
        if sequence != 1:
            kwargs["sequence"] = sequence
        result = save(**kwargs)
    except InterviewPolicyError:
        return _policy_conflict_response(request)
    except FirstAnswerPersistenceError:
        form.add_error(None, "답변을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.")
        return _question_response(request, interview, turn, form, status=503)
    except FirstAnswerConflict as error:
        return _saved_response(request, interview, error.turn, status=409)
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "reflections/_interview_answer_saved.html",
            {"turn": result.turn},
        )
    return redirect("reflections:interview_detail", interview_id=interview.pk)


@require_POST
@login_required
def turn_skip(request: HttpRequest, interview_id: int, sequence: int) -> HttpResponse:
    """현재 Turn을 건너뛰고 다음 질문 또는 종료 상태로 전이한다."""
    interview = get_object_or_404(
        Interview.objects.select_related("reading", "book"),
        pk=interview_id,
        reading__user=request.user,
    )
    turn = get_object_or_404(interview.turns, sequence=sequence)

    if set(request.POST) - {"csrfmiddlewaretoken"}:
        return _policy_conflict_response(request)

    try:
        result = skip_interview_turn(
            user=request.user,
            interview=interview,
            sequence=sequence,
        )
    except InterviewPolicyError:
        return _policy_conflict_response(request)
    except (
        QuestionGenerationError,
        NextTurnPersistenceError,
        NextTurnStaleError,
    ) as error:
        _log_pipeline_failure("skip", interview.pk, sequence, error)
        template = (
            "reflections/_interview_skip_error.html"
            if request.headers.get("HX-Request") == "true"
            else "reflections/interview_detail.html"
        )
        return _interview_turn_response(
            request,
            template,
            {
                "interview": interview,
                "turn": turn,
                "previous_turns": _get_previous_turns(interview, turn),
                "skip_error": True,
                **_pipeline_failure_details(error),
            },
            status=503,
            focus_error=True,
        )

    if request.headers.get("HX-Request") == "true":
        interview.refresh_from_db()
        if result.destination == InterviewDestination.ENDED_NO_REFLECTION:
            return render(
                request,
                "reflections/_interview_ended_no_reflection.html",
                {"interview": interview},
            )
        if result.destination == InterviewDestination.REFLECTION_READY:
            return render(
                request,
                "reflections/_interview_reflection_ready.html",
                {"interview": interview},
            )
        current = result.next_turn or interview.turns.order_by("-sequence").first()
        choice = InterviewProgressDecision.objects.filter(
            turn=result.skipped_turn, selection__isnull=True
        ).first()
        if choice is not None:
            return render(
                request,
                (
                    "reflections/_interview_soft_stop.html"
                    if choice.kind == InterviewProgressDecision.Kind.SOFT_STOP
                    else "reflections/_interview_cap_extension.html"
                ),
                {"turn": result.skipped_turn},
            )
        return render(
            request,
            "reflections/_interview_question.html",
            {
                "interview": interview,
                "turn": current,
                "answer_form": FirstAnswerForm(),
            },
        )

    return redirect("reflections:interview_detail", interview_id=interview.pk)


@require_POST
@login_required
def next_turn(request: HttpRequest, interview_id: int, sequence: int) -> HttpResponse:
    """확정 답변의 후속 단계를 처리하고 현재 상태를 반환한다."""
    interview = get_object_or_404(
        Interview.objects.select_related("reading", "book"),
        pk=interview_id,
        reading__user=request.user,
    )
    turn = get_object_or_404(interview.turns, sequence=sequence)
    try:
        process_next_turn(user=request.user, interview=interview, turn=turn)
    except InterviewPolicyError, AnswerAnalysisPolicyError:
        return _policy_conflict_response(request)
    except (
        AnswerAnalysisError,
        QuestionGenerationError,
        NextTurnPersistenceError,
        NextTurnStaleError,
    ) as error:
        _log_pipeline_failure("next", interview.pk, sequence, error)
        template = (
            "reflections/_interview_next_error.html"
            if request.headers.get("HX-Request") == "true"
            else "reflections/interview_detail.html"
        )
        return _interview_turn_response(
            request,
            template,
            {
                "interview": interview,
                "turn": turn,
                "previous_turns": _get_previous_turns(interview, turn),
                "next_error": True,
                **_pipeline_failure_details(error),
            },
            status=503,
            focus_error=True,
        )
    if request.headers.get("HX-Request") == "true":
        interview.refresh_from_db()
        current = interview.turns.order_by("-sequence").first()
        if interview.status == Interview.Status.REFLECTION_READY:
            return render(
                request,
                "reflections/_interview_reflection_ready.html",
                {"interview": interview},
            )
        choice = InterviewProgressDecision.objects.filter(
            turn=current, selection__isnull=True
        ).first()
        if choice is not None:
            return render(
                request,
                (
                    "reflections/_interview_soft_stop.html"
                    if choice.kind == InterviewProgressDecision.Kind.SOFT_STOP
                    else "reflections/_interview_cap_extension.html"
                ),
                {"turn": current},
            )
        if current.next_question_skipped_at is not None:
            return render(
                request,
                "reflections/_interview_question_skipped.html",
                {"turn": current},
            )
        if current.answer is not None:
            return render(
                request,
                "reflections/_interview_answer_saved.html",
                {"turn": current},
            )
        return render(
            request,
            "reflections/_interview_question.html",
            {
                "interview": interview,
                "turn": current,
                "answer_form": FirstAnswerForm(),
            },
        )
    return redirect("reflections:interview_detail", interview_id=interview.pk)


@require_POST
@login_required
def interview_decision(
    request: HttpRequest, interview_id: int, sequence: int
) -> HttpResponse:
    """소유자의 종료·계속 선택을 확정하고 같은 Interview 상태를 반환한다."""
    interview = get_object_or_404(
        Interview.objects.select_related("reading", "book"),
        pk=interview_id,
        reading__user=request.user,
    )
    if set(request.POST) - {"csrfmiddlewaretoken", "decision"}:
        return _policy_conflict_response(request)
    try:
        result = decide_interview_progress(
            user=request.user,
            interview=interview,
            sequence=sequence,
            decision=request.POST.get("decision", ""),
        )
    except InterviewPolicyError:
        return _policy_conflict_response(request)
    except NextTurnPersistenceError:
        turn = get_object_or_404(interview.turns, sequence=sequence)
        template = (
            "reflections/_interview_next_error.html"
            if request.headers.get("HX-Request") == "true"
            else "reflections/interview_detail.html"
        )
        return _interview_turn_response(
            request,
            template,
            {
                "interview": interview,
                "turn": turn,
                "previous_turns": _get_previous_turns(interview, turn),
                "next_error": True,
            },
            status=503,
            focus_error=True,
        )
    if request.headers.get("HX-Request") == "true":
        if result.skipped:
            return render(
                request,
                "reflections/_interview_reflection_ready.html",
                {"interview": interview},
            )
        return render(
            request,
            "reflections/_interview_question.html",
            {
                "interview": interview,
                "turn": result.turn,
                "answer_form": FirstAnswerForm(),
            },
        )
    return redirect("reflections:interview_detail", interview_id=interview.pk)


def _get_previous_turns(
    interview: Interview, turn: InterviewTurn | None
) -> list[InterviewTurn]:
    """재진입 시 현재 단계 이전의 확정된 질문·답변 목록을 순서대로 반환한다."""
    if turn is None:
        return []
    return list(
        interview.turns.filter(
            sequence__lt=turn.sequence,
            answer__isnull=False,
        ).order_by("sequence")
    )


def _destination_response(
    request: HttpRequest, interview: Interview, *, detail: bool = False
) -> HttpResponse:
    if interview.book_id != interview.reading.book_id:
        return render(
            request,
            "reflections/interview_unavailable.html",
            {"label": "인터뷰 정보"},
            status=400,
        )
    try:
        destination = get_interview_destination(interview)
    except InterviewPolicyError:
        return render(
            request,
            "reflections/interview_unavailable.html",
            {"label": "현재 단계"},
            status=409,
        )
    if destination is InterviewDestination.INTERVIEW:
        if detail:
            turn = interview.turns.order_by("-sequence").first()
            if turn is not None and turn.next_question_skipped_at is not None:
                existing_ref = Reflection.objects.filter(interview=interview).first()
                if existing_ref is not None:
                    return redirect(
                        "reflections:reflection_detail", reflection_id=existing_ref.pk
                    )
                return render(
                    request,
                    "reflections/interview_reflection_ready.html",
                    {"interview": interview},
                )
            choice = (
                InterviewProgressDecision.objects.filter(
                    turn=turn, selection__isnull=True
                ).first()
                if turn is not None
                else None
            )
            return render(
                request,
                "reflections/interview_detail.html",
                {
                    "interview": interview,
                    "turn": turn,
                    "previous_turns": _get_previous_turns(interview, turn),
                    "answer_form": FirstAnswerForm(),
                    "progress_decision": choice,
                },
            )
        return redirect("reflections:interview_detail", interview_id=interview.pk)
    if destination is InterviewDestination.REFLECTION_READY:
        existing_ref = Reflection.objects.filter(interview=interview).first()
        if existing_ref is not None:
            return redirect(
                "reflections:reflection_detail", reflection_id=existing_ref.pk
            )
        return render(
            request,
            "reflections/interview_reflection_ready.html",
            {"interview": interview},
        )
    if destination is InterviewDestination.ENDED_NO_REFLECTION:
        return render(
            request,
            "reflections/interview_ended_no_reflection.html",
            {"interview": interview},
        )
    label = "완료된 Reflection 단계"
    return render(
        request, "reflections/interview_unavailable.html", {"label": label}, status=409
    )


def _question_response(
    request: HttpRequest,
    interview: Interview,
    turn,
    form: FirstAnswerForm,
    *,
    status: int,
) -> HttpResponse:
    _prepare_answer_form_accessibility(form)
    context = {
        "interview": interview,
        "turn": turn,
        "previous_turns": _get_previous_turns(interview, turn),
        "answer_form": form,
    }
    template = (
        "reflections/_interview_question.html"
        if request.headers.get("HX-Request") == "true"
        else "reflections/interview_detail.html"
    )
    return _interview_turn_response(
        request, template, context, status=status, focus_error=bool(form.errors)
    )


def _saved_response(
    request: HttpRequest, interview: Interview, turn, *, status: int
) -> HttpResponse:
    template = (
        "reflections/_interview_answer_saved.html"
        if request.headers.get("HX-Request") == "true"
        else "reflections/interview_detail.html"
    )
    return _interview_turn_response(
        request,
        template,
        {
            "interview": interview,
            "turn": turn,
            "previous_turns": _get_previous_turns(interview, turn),
        },
        status=status,
    )


def _question_error_response(
    request: HttpRequest, interview: Interview, error: Exception
) -> HttpResponse:
    template = (
        "reflections/_interview_error.html"
        if request.headers.get("HX-Request") == "true"
        else "reflections/interview_detail.html"
    )
    return _interview_turn_response(
        request,
        template,
        {
            "interview": interview,
            "question_error": True,
            **_pipeline_failure_details(error),
        },
        status=503,
        focus_error=True,
    )


def _policy_conflict_response(request: HttpRequest) -> HttpResponse:
    """정책 충돌의 내부 사유를 숨기고 요청 방식에 맞는 409를 반환한다."""
    is_htmx = request.headers.get("HX-Request") == "true"
    template = (
        "reflections/_interview_unavailable.html"
        if is_htmx
        else "reflections/interview_unavailable.html"
    )
    return _interview_turn_response(
        request,
        template,
        {"label": "현재 단계"},
        status=409,
        focus_error=is_htmx,
    )


def _prepare_answer_form_accessibility(form: FirstAnswerForm) -> None:
    """오류가 있는 bound 답변 form의 설명·focus 대상을 연결한다."""
    if not form.errors:
        return
    descriptions = ["answer-help"]
    if form.non_field_errors():
        descriptions.append("answer-form-error")
    if form.errors.get("answer"):
        descriptions.append("id_answer-error")
        form.fields["answer"].widget.attrs["aria-invalid"] = "true"
    form.fields["answer"].widget.attrs["aria-describedby"] = " ".join(descriptions)
    form.fields["answer"].widget.attrs["data-interview-focus"] = "true"


def _interview_turn_response(
    request: HttpRequest,
    template: str,
    context: dict[str, object],
    *,
    status: int,
    focus_error: bool = False,
) -> HttpResponse:
    """HTMX 오류도 Interview region 전체 교체로 회복할 수 있게 반환한다."""
    response = render(request, template, context, status=status)
    if request.headers.get("HX-Request") == "true" and status >= 400:
        response.headers["HX-Retarget"] = "#interview-turn-region"
        response.headers["HX-Reswap"] = "outerHTML"
        if focus_error:
            response.headers["HX-Trigger-After-Settle"] = "interviewTurnSettled"
    return response


@login_required
@require_POST
def reflection_generate(request: HttpRequest, interview_id: int) -> HttpResponse:
    interview = (
        Interview.objects.filter(pk=interview_id, reading__user=request.user)
        .select_related("reading__book")
        .first()
    )
    if interview is None:
        raise Http404("Interview not found or access denied")

    if set(request.POST) - {"csrfmiddlewaretoken"}:
        return _policy_conflict_response(request)

    if interview.status != Interview.Status.REFLECTION_READY:
        return _policy_conflict_response(request)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        result = generate_or_get_reflection_draft(
            user=request.user,
            interview=interview,
        )
        target_url = reverse(
            "reflections:reflection_detail", args=[result.reflection.pk]
        )
        if is_htmx:
            response = HttpResponse(status=200)
            response.headers["HX-Redirect"] = target_url
            return response
        return redirect(target_url)
    except Exception as error:
        _log_pipeline_failure("reflection_generate", interview.pk, 0, error)
        context = {
            "interview": interview,
            "reflection_error": True,
            **_pipeline_failure_details(error),
        }
        if is_htmx:
            response = render(
                request,
                "reflections/_reflection_generation_error.html",
                context,
                status=503,
            )
            response.headers["HX-Retarget"] = "#interview-turn-region"
            response.headers["HX-Reswap"] = "outerHTML"
            response.headers["HX-Trigger-After-Settle"] = "reflectionErrorSettled"
            return response
        return render(
            request,
            "reflections/interview_reflection_ready.html",
            context,
            status=503,
        )


@login_required
@require_GET
def reflection_detail(request: HttpRequest, reflection_id: int) -> HttpResponse:
    reflection = (
        Reflection.objects.filter(
            pk=reflection_id, interview__reading__user=request.user
        )
        .select_related("interview__reading__book")
        .first()
    )
    if reflection is None:
        raise Http404("Reflection not found or access denied")

    return render(
        request,
        "reflections/reflection_draft_ready.html",
        {
            "reflection": reflection,
            "book": reflection.interview.reading.book,
        },
    )
