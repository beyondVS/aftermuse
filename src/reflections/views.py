from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from integrations.llm.contracts import QuestionGenerationError
from integrations.llm.factory import get_question_provider
from knowledge.services import get_book_knowledge_readiness
from readings.models import Reading
from reflections.forms import FirstAnswerForm
from reflections.models import Interview
from reflections.services import (
    InterviewDestination,
    InterviewPolicyError,
    ensure_first_question,
    get_interview_destination,
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
            user=request.user, interview=interview, provider=get_question_provider()
        )
    except InterviewPolicyError:
        return render(request, "reflections/interview_unavailable.html", status=409)
    except QuestionGenerationError:
        return render(
            request,
            "reflections/_interview_error.html",
            {"interview": interview},
            status=503,
        )
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
            turn = interview.turns.filter(sequence=1).first()
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
