from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from accounts.forms import SignupForm


def signup(request: HttpRequest) -> HttpResponse:
    """유효한 회원가입을 완료한 사용자를 즉시 로그인한다."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, "accounts/signup.html", {"form": form})
