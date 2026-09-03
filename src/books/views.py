from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.vary import vary_on_headers

from books.forms import BookSearchForm
from books.services import search_books
from integrations.aladin.client import get_default_provider


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
            search_result = search_books(
                search_query,
                get_default_provider(),
            )
            context["search_query"] = search_query
            context["search_result"] = search_result
            context["search_state"] = search_result.status.value
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
