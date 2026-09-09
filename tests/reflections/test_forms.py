from reflections.forms import FirstAnswerForm


def test_answer_form_rejects_missing_or_whitespace_only_answer() -> None:
    assert not FirstAnswerForm(data={}).is_valid()
    form = FirstAnswerForm(data={"answer": "   \n\t"})

    assert not form.is_valid()
    assert "answer" in form.errors


def test_answer_form_preserves_raw_answer_and_2000_character_boundary() -> None:
    prefix = " 앞뒤 공백을 보존합니다 "
    answer = prefix + "가" * (2000 - len(prefix))
    form = FirstAnswerForm(data={"answer": answer})

    assert form.is_valid()
    assert form.cleaned_data["answer"] == answer
    assert form["answer"].value() == answer
    assert not FirstAnswerForm(data={"answer": "가" * 2001}).is_valid()
