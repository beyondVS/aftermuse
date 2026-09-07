from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.vary import vary_on_headers

from books.forms import BookSearchForm, BookSelectionForm
from books.selection_candidates import (
    SelectionCandidateError,
    clear_candidates,
    get_candidate,
    store_candidates,
)
from books.services import BookSearchStatus, search_books, select_book
from integrations.book_metadata.factory import get_default_provider


@require_GET
@login_required
@vary_on_headers("HX-Request")
def search(request: HttpRequest) -> HttpResponse:
    """검증된 검색어의 도서 Metadata를 전체 페이지 또는 HTMX Fragment로 제공한다."""
    is_submitted = "q" in request.GET
    form = BookSearchForm(request.GET if is_submitted else None)
    context: dict[str, object] = {
        "form": form,
        "search_result": None,
        "search_state": "initial",
        "search_query": "",
    }

    if is_submitted:
        if form.is_valid():
            search_query = form.cleaned_data["q"]
            clear_candidates(request.session)
            search_result = search_books(
                search_query,
                get_default_provider(),
            )
            context["search_query"] = search_query
            context["search_result"] = search_result
            context["search_state"] = search_result.status.value
            if search_result.status is BookSearchStatus.SUCCESS:
                selection_candidates = store_candidates(
                    request.session,
                    str(request.user.pk),
                    search_result.books,
                )
                context["search_result_candidates"] = tuple(
                    zip(search_result.books, selection_candidates, strict=True)
                )
        else:
            form.fields["q"].widget.attrs["aria-describedby"] = (
                "search-query-help search-query-error"
            )
            context["search_state"] = "input_error"

    template_name = (
        "books/_search_region.html"
        if request.headers.get("HX-Request") == "true"
        else "books/search.html"
    )
    return render(request, template_name, context)


@require_POST
@login_required
@vary_on_headers("HX-Request")
def select(request: HttpRequest) -> HttpResponse:
    """보관된 후보 ID만으로 Book 선택을 처리하고 안전한 결과를 반환한다."""
    form = BookSelectionForm(request.POST)
    context: dict[str, object] = {
        "form": BookSearchForm(),
        "search_result": None,
        "search_state": "initial",
        "search_query": "",
        "selection_state": "invalid",
    }
    if form.is_valid():
        try:
            candidate = get_candidate(
                request.session,
                str(request.user.pk),
                str(form.cleaned_data["candidate_id"]),
            )
        except SelectionCandidateError:
            pass
        else:
            try:
                selection_result = select_book(candidate)
            except DatabaseError:
                context["selection_state"] = "error"
                context["retry_candidate_id"] = form.cleaned_data["candidate_id"]
            else:
                entry_url = reverse(
                    "readings:book_entry", args=[selection_result.book.pk]
                )
                if request.headers.get("HX-Request") == "true":
                    response = HttpResponse()
                    response["HX-Redirect"] = entry_url
                    return response
                return redirect(entry_url)

    template_name = (
        "books/_search_region.html"
        if request.headers.get("HX-Request") == "true"
        else "books/search.html"
    )
    return render(request, template_name, context)
