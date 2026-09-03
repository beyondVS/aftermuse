from django import forms


class BookSearchForm(forms.Form):
    """도서 검색에 사용할 정규화된 검색어를 검증한다."""

    q = forms.CharField(
        label="도서 검색",
        max_length=200,
        error_messages={
            "required": "검색어를 입력해 주세요.",
            "max_length": "검색어는 200자 이하로 입력해 주세요.",
        },
        widget=forms.SearchInput(
            attrs={
                "aria-describedby": "search-query-help",
                "maxlength": 200,
            }
        ),
    )

    def clean_q(self) -> str:
        """양끝 공백을 제거한 검색어를 반환한다."""
        return self.cleaned_data["q"].strip()
