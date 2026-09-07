from datetime import date

from django import forms

from readings.models import Reading


class ReadingStartForm(forms.Form):
    """첫 Reading 또는 재독을 시작할 때의 명시적 상태 선택을 검증한다."""

    status = forms.ChoiceField(
        label="지금의 독서 상태",
        choices=Reading.Status.choices,
        widget=forms.RadioSelect,
    )
    completed_on = forms.DateField(
        label="완독일",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["completed_on"].widget.attrs["max"] = date.today().isoformat()

    def clean(self) -> dict[str, object]:
        """선택 상태에 필요한 완독일과 미래 날짜를 함께 검증한다."""
        cleaned_data = super().clean()
        _validate_completion_date(cleaned_data, self)
        return cleaned_data


class ReadingStateForm(ReadingStartForm):
    """현재 Reading의 상태를 바꿀 때 상태와 완독일을 검증한다."""


class CompletionDateForm(forms.Form):
    """완독 Reading의 날짜만 명시적으로 수정하는 입력을 검증한다."""

    completed_on = forms.DateField(
        label="완독일",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_completed_on(self) -> date:
        """오늘 이후의 완독일을 거부한다."""
        completed_on = self.cleaned_data["completed_on"]
        if completed_on > date.today():
            raise forms.ValidationError("완독일은 오늘 이후로 지정할 수 없습니다.")
        return completed_on


def _validate_completion_date(
    cleaned_data: dict[str, object], form: forms.Form
) -> None:
    """상태와 완독일의 조합을 Form 오류로 표현한다."""
    status = cleaned_data.get("status")
    completed_on = cleaned_data.get("completed_on")
    if status == Reading.Status.COMPLETED:
        if completed_on is None:
            form.add_error("completed_on", "완독 상태에는 완독일이 필요합니다.")
        elif isinstance(completed_on, date) and completed_on > date.today():
            form.add_error("completed_on", "완독일은 오늘 이후로 지정할 수 없습니다.")
    elif completed_on is not None:
        form.add_error(
            "completed_on", "완독이 아닌 상태에는 완독일을 지정할 수 없습니다."
        )
