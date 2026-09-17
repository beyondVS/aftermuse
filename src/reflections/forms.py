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


class ReflectionRevisionForm(forms.Form):
    """사용자가 작성한 Reflection 본문 수정을 검증한다."""

    markdown = forms.CharField(
        label="독서노트 본문",
        strip=False,
        max_length=20000,
        error_messages={
            "required": "본문은 공백만으로 구성될 수 없습니다.",
            "max_length": "20,000자를 초과할 수 없습니다.",
        },
        widget=forms.Textarea(
            attrs={
                "rows": 18,
                "aria-describedby": "markdown-help",
                "placeholder": "독서노트 본문을 수정해 보세요.",
            }
        ),
    )

    def clean_markdown(self) -> str:
        """공백만 입력된 본문과 20,000자 초과 입력을 거부하되 원문 서식을 보존한다."""
        markdown_text = self.cleaned_data.get("markdown", "")
        if not markdown_text or not markdown_text.strip():
            raise forms.ValidationError("본문은 공백만으로 구성될 수 없습니다.")
        if len(markdown_text) > 20000:
            raise forms.ValidationError("20,000자를 초과할 수 없습니다.")
        return markdown_text
