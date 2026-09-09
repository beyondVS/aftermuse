"""첫 Interview Turn 답변 입력 경계를 정의한다."""

from django import forms


class FirstAnswerForm(forms.Form):
    """사용자가 작성한 첫 답변의 원문을 검증하고 보존한다."""

    answer = forms.CharField(
        label="내 생각",
        max_length=2000,
        strip=False,
        widget=forms.Textarea(
            attrs={
                "rows": 7,
                "aria-describedby": "answer-help",
                "placeholder": "떠오르는 장면이나 생각을 자유롭게 적어 보세요.",
            }
        ),
    )

    def clean_answer(self) -> str:
        """공백만 입력된 답변은 거부하되 원문을 변경하지 않는다."""
        answer = self.cleaned_data["answer"]
        if not answer.strip():
            raise forms.ValidationError("내용을 한 글자 이상 입력해 주세요.")
        return answer
