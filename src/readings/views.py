from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.vary import vary_on_headers

from books.models import Book
from readings.forms import CompletionDateForm, ReadingStartForm, ReadingStateForm
from readings.models import Reading
from readings.services import (
    ActiveReadingExistsError,
    ReadingHistoryExistsError,
    ReadingLockedError,
    ReadingPolicyError,
    change_reading_state,
    create_initial_reading,
    create_rereading,
    update_completion_date,
)


@require_GET
@login_required
def book_entry(request: HttpRequest, book_id: int) -> HttpResponse:
    """선택한 Book의 현재 Reading 이력에 맞는 시작 또는 계속 화면을 제공한다."""
    book = get_object_or_404(Book, pk=book_id)
    readings = list(
        Reading.objects.filter(user=request.user, book=book).order_by(
            "-completed_on", "-created_at", "-pk"
        )
    )
    active_reading = next((reading for reading in readings if reading.is_active), None)
    context: dict[str, object] = {"book": book, "start_form": ReadingStartForm()}
    if active_reading is not None:
        context["active_reading"] = active_reading
    elif readings:
        context["latest_completed_reading"] = readings[0]
    return render(request, "readings/book_entry.html", context)


@require_POST
@login_required
def create(request: HttpRequest, book_id: int) -> HttpResponse:
    """이력이 없는 Book의 첫 Reading 생성을 Form과 Service로 조합한다."""
    book = get_object_or_404(Book, pk=book_id)
    form = ReadingStartForm(request.POST)
    if form.is_valid():
        try:
            result = create_initial_reading(
                user=request.user,
                book=book,
                status=form.cleaned_data["status"],
                completed_on=form.cleaned_data["completed_on"],
            )
        except ReadingHistoryExistsError as error:
            return redirect("readings:detail", reading_id=error.reading.pk)
        except ActiveReadingExistsError as error:
            return redirect("readings:detail", reading_id=error.reading.pk)
        except ReadingPolicyError:
            form.add_error(None, "독서 상태를 저장할 수 없습니다. 다시 확인해 주세요.")
        except DatabaseError:
            form.add_error(None, "잠시 후 다시 시도해 주세요.")
        else:
            return redirect("readings:detail", reading_id=result.reading.pk)
    return render(
        request,
        "readings/book_entry.html",
        {"book": book, "start_form": form},
        status=400,
    )


@require_GET
@login_required
@vary_on_headers("HX-Request")
def detail(request: HttpRequest, reading_id: int) -> HttpResponse:
    """소유자만 Reading 상태를 볼 수 있는 전체 상세 또는 HTMX panel을 제공한다."""
    reading = get_object_or_404(
        Reading.objects.select_related("book"), pk=reading_id, user=request.user
    )
    return _render_detail(request, reading)


@require_POST
@login_required
def reread(request: HttpRequest, reading_id: int) -> HttpResponse:
    """소유한 완독 Reading에서만 명시적인 재독을 시작한다."""
    source = get_object_or_404(
        Reading.objects.select_related("book"),
        pk=reading_id,
        user=request.user,
        status=Reading.Status.COMPLETED,
    )
    form = ReadingStartForm(request.POST)
    if form.is_valid():
        try:
            result = create_rereading(
                user=request.user,
                source_reading=source,
                status=form.cleaned_data["status"],
                completed_on=form.cleaned_data["completed_on"],
            )
        except ActiveReadingExistsError as error:
            return redirect("readings:detail", reading_id=error.reading.pk)
        except ReadingHistoryExistsError, ReadingPolicyError:
            form.add_error(
                None, "다시 읽기를 시작할 수 없습니다. 화면을 새로고침해 주세요."
            )
        except DatabaseError:
            form.add_error(None, "잠시 후 다시 시도해 주세요.")
        else:
            return redirect("readings:detail", reading_id=result.reading.pk)
    return _render_detail(request, source, reread_form=form, status=400)


@require_POST
@login_required
@vary_on_headers("HX-Request")
def change_state(request: HttpRequest, reading_id: int) -> HttpResponse:
    """소유 Reading의 상태 또는 명시적 완독일 수정 결과를 반환한다."""
    reading = get_object_or_404(
        Reading.objects.select_related("book"), pk=reading_id, user=request.user
    )
    if request.POST.get("intent") == "update_completed_on":
        date_form = CompletionDateForm(request.POST, prefix="completion")
        state_form = ReadingStateForm(initial=_state_initial(reading))
        if date_form.is_valid():
            try:
                reading = update_completion_date(
                    user=request.user,
                    reading=reading,
                    completed_on=date_form.cleaned_data["completed_on"],
                )
            except ReadingPolicyError as error:
                return _policy_error_response(
                    request, reading, state_form, date_form, error
                )
            except DatabaseError:
                date_form.add_error(None, "잠시 후 다시 시도해 주세요.")
            else:
                return _render_detail(
                    request, reading, success_message="완독일을 저장했습니다."
                )
        return _render_detail(
            request, reading, state_form=state_form, date_form=date_form, status=400
        )

    state_form = ReadingStateForm(request.POST)
    date_form = CompletionDateForm(
        initial={"completed_on": reading.completed_on}, prefix="completion"
    )
    if state_form.is_valid():
        try:
            reading = change_reading_state(
                user=request.user,
                reading=reading,
                status=state_form.cleaned_data["status"],
                completed_on=state_form.cleaned_data["completed_on"],
            )
        except ReadingPolicyError as error:
            return _policy_error_response(
                request, reading, state_form, date_form, error
            )
        except DatabaseError:
            state_form.add_error(None, "잠시 후 다시 시도해 주세요.")
        else:
            return _render_detail(
                request, reading, success_message="독서 상태를 저장했습니다."
            )
    return _render_detail(
        request, reading, state_form=state_form, date_form=date_form, status=400
    )


def _policy_error_response(
    request: HttpRequest,
    reading: Reading,
    state_form: ReadingStateForm,
    date_form: CompletionDateForm,
    error: ReadingPolicyError,
) -> HttpResponse:
    conflict_reading = None
    if isinstance(error, ActiveReadingExistsError):
        state_form.add_error(
            None, "진행 중인 다른 Reading이 있어 상태를 바꿀 수 없습니다."
        )
        conflict_reading = (
            Reading.objects.filter(
                pk=error.reading.pk,
                user=request.user,
                book=reading.book,
                status__in=(Reading.Status.WANT_TO_READ, Reading.Status.READING),
            )
            .select_related("book")
            .first()
        )
    elif isinstance(error, ReadingLockedError):
        state_form.add_error(None, "인터뷰가 시작되어 완독 정보는 수정할 수 없습니다.")
    else:
        state_form.add_error(None, "요청한 상태로 바꿀 수 없습니다.")
    return _render_detail(
        request,
        reading,
        state_form=state_form,
        date_form=date_form,
        conflict_reading=conflict_reading,
        status=400,
    )


def _render_detail(
    request: HttpRequest,
    reading: Reading,
    *,
    state_form: ReadingStateForm | None = None,
    date_form: CompletionDateForm | None = None,
    reread_form: ReadingStartForm | None = None,
    conflict_reading: Reading | None = None,
    success_message: str | None = None,
    status: int = 200,
) -> HttpResponse:
    context = {
        "reading": reading,
        "state_form": state_form or ReadingStateForm(initial=_state_initial(reading)),
        "date_form": date_form
        or CompletionDateForm(
            initial={"completed_on": reading.completed_on}, prefix="completion"
        ),
        "reread_form": reread_form or ReadingStartForm(prefix="reread"),
        "conflict_reading": conflict_reading,
        "success_message": success_message,
    }
    is_htmx = request.headers.get("HX-Request") == "true"
    template_name = (
        "readings/_reading_panel.html" if is_htmx else "readings/detail.html"
    )
    response = render(request, template_name, context, status=status)
    if is_htmx:
        response.headers["HX-Trigger-After-Settle"] = "readingPanelSettled"
    if is_htmx and 400 <= status < 500:
        # HTMX 2.x는 기본적으로 4xx body를 swap하지 않으므로, app.js가 이 제한된
        # 표준 header 조합에만 응답해 Reading panel 교체를 허용한다.
        response.headers["HX-Retarget"] = "#reading-panel"
        response.headers["HX-Reswap"] = "outerHTML"
    return response


def _state_initial(reading: Reading) -> dict[str, object]:
    return {"status": reading.status, "completed_on": reading.completed_on}
