from datetime import date, timedelta

from readings.forms import CompletionDateForm, ReadingStartForm
from readings.models import Reading


def test_start_form_requires_date_only_for_completed_status() -> None:
    completed = ReadingStartForm({"status": Reading.Status.COMPLETED})
    active = ReadingStartForm({"status": Reading.Status.READING})

    assert not completed.is_valid()
    assert "completed_on" in completed.errors
    assert active.is_valid()


def test_start_form_defaults_completion_date_to_today() -> None:
    form = ReadingStartForm()

    assert form.initial["completed_on"] == date.today()


def test_start_form_ignores_only_the_prefilled_date_for_active_status() -> None:
    default_date = ReadingStartForm(
        {"status": Reading.Status.READING, "completed_on": date.today()}
    )
    explicit_date = ReadingStartForm(
        {
            "status": Reading.Status.READING,
            "completed_on": date.today() - timedelta(days=1),
        }
    )

    assert default_date.is_valid()
    assert default_date.cleaned_data["completed_on"] is None
    assert not explicit_date.is_valid()
    assert "completed_on" in explicit_date.errors


def test_completion_date_form_rejects_future_date() -> None:
    form = CompletionDateForm({"completed_on": date.today() + timedelta(days=1)})

    assert not form.is_valid()
    assert "completed_on" in form.errors
