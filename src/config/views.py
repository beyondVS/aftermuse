from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """초기 설정 확인 페이지 또는 HTMX partial을 반환한다."""
    template_name = (
        "pages/home.html#setup-status"
        if request.headers.get("HX-Request") == "true"
        else "pages/home.html"
    )
    return render(request, template_name)
