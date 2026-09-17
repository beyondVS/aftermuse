from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from readings.models import Reading
from reflections.models import Interview, InterviewProgressDecision, Reflection


def _get_interview_stage_label(interview: Interview) -> str:
    """진행 중 인터뷰의 현재 진행 단계를 사용자에게 요약한다."""
    turns = list(interview.turns.all())
    if not turns:
        return "첫 질문 준비"
    latest_turn = max(turns, key=lambda t: t.sequence)
    if latest_turn.answer is None:
        return f"{latest_turn.sequence}번째 질문 답변 대기"
    choice = getattr(latest_turn, "progress_decision", None)
    if choice and choice.selection is None:
        if choice.kind == InterviewProgressDecision.Kind.SOFT_STOP:
            return "조기 마무리 선택 대기"
        return "질문 상한 선택 대기"
    return f"{latest_turn.sequence}번째 질문 답변 완료"


def get_home_reading_groups(user) -> dict[str, object]:
    """현재 사용자의 Reading 및 진행 중 Interview를 분류하여 반환한다."""
    readings = (
        Reading.objects.filter(user=user)
        .select_related("book", "interview", "interview__book")
        .prefetch_related(
            "interview__turns",
            "interview__turns__progress_decision",
        )
        .order_by("-updated_at", "-id")
    )

    currently_reading: list[Reading] = []
    ready_for_reflection: list[Reading] = []
    in_progress_interviews: list[Interview] = []

    has_any_readings = False
    for reading in readings:
        has_any_readings = True
        if reading.status in (Reading.Status.WANT_TO_READ, Reading.Status.READING):
            currently_reading.append(reading)
        elif reading.status == Reading.Status.COMPLETED:
            interview = getattr(reading, "interview", None)
            if interview is None:
                ready_for_reflection.append(reading)
            elif interview.status == Interview.Status.IN_PROGRESS:
                interview.stage_display = _get_interview_stage_label(interview)
                in_progress_interviews.append(interview)

    in_progress_interviews.sort(
        key=lambda item: (item.updated_at, item.id), reverse=True
    )

    recent_reflection = (
        Reflection.objects.filter(interview__reading__user=user)
        .select_related("interview__reading__book")
        .order_by("-updated_at", "-id")
        .first()
    )

    return {
        "currently_reading": currently_reading,
        "ready_for_reflection": ready_for_reflection,
        "in_progress_interviews": in_progress_interviews,
        "recent_reflection": recent_reflection,
        "has_any_readings": has_any_readings,
    }


def home(request: HttpRequest) -> HttpResponse:
    """초기 설정 확인 페이지 또는 HTMX partial을 반환한다."""
    template_name = (
        "pages/home.html#setup-status"
        if request.headers.get("HX-Request") == "true"
        else "pages/home.html"
    )
    if request.headers.get("HX-Request") == "true":
        return render(request, template_name)

    context: dict[str, object] = {}
    if request.user.is_authenticated:
        context.update(get_home_reading_groups(request.user))

    return render(request, template_name, context)
