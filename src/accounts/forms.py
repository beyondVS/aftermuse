from django.contrib.auth.forms import UserCreationForm

from accounts.models import User


class SignupForm(UserCreationForm):
    """AfterMuse의 아이디 기반 회원가입 입력을 검증한다."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)
        labels = {"username": "아이디"}
