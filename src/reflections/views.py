from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from integrations.llm.contracts import AnswerAnalysisError, QuestionGenerationError
from integrations.llm.factory import get_question_provider
from knowledge.services import get_book_knowledge_readiness
from readings.models import Reading
from reflections.forms import FirstAnswerForm
from reflections.models import Interview
from reflections.services import (
    FirstAnswerConflict,
    FirstAnswerPersistenceError,
    InterviewDestination,
    InterviewPolicyError,
    NextTurnPersistenceError,
    NextTurnStaleError,
    ensure_first_question,
    get_interview_destination,
    process_next_turn,
    save_first_answer,
    save_turn_answer,
    start_interview,
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
    except QuestionGenerationError:
        return _question_error_response(request, interview)
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
    except InterviewPolicyError:
        return _policy_conflict_response(request)
    except (
        AnswerAnalysisError,
        QuestionGenerationError,
        NextTurnPersistenceError,
        NextTurnStaleError,
    ):
        template = (
            "reflections/_interview_next_error.html"
            if request.headers.get("HX-Request") == "true"
            else "reflections/interview_detail.html"
        )
        return _interview_turn_response(
            request,
            template,
            {"interview": interview, "turn": turn, "next_error": True},
            status=503,
            focus_error=True,
        )
    if request.headers.get("HX-Request") == "true":
        current = interview.turns.order_by("-sequence").first()
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
            return render(
                request,
                "reflections/interview_detail.html",
                {
                    "interview": interview,
                    "turn": turn,
                    "answer_form": FirstAnswerForm(),
                },
            )
        return redirect("reflections:interview_detail", interview_id=interview.pk)
    label = (
        "Reflection 준비 단계"
        if destination is InterviewDestination.REFLECTION_READY
        else "완료된 Reflection 단계"
    )
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
    context = {"interview": interview, "turn": turn, "answer_form": form}
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
        request, template, {"interview": interview, "turn": turn}, status=status
    )


def _question_error_response(
    request: HttpRequest, interview: Interview
) -> HttpResponse:
    template = (
        "reflections/_interview_error.html"
        if request.headers.get("HX-Request") == "true"
        else "reflections/interview_detail.html"
    )
    return _interview_turn_response(
        request,
        template,
        {"interview": interview, "question_error": True},
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
