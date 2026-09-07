from datetime import date, timedelta

from readings.forms import CompletionDateForm, ReadingStartForm
from readings.models import Reading


def test_start_form_requires_date_only_for_completed_status() -> None:
    completed = ReadingStartForm({"status": Reading.Status.COMPLETED})
    active = ReadingStartForm({"status": Reading.Status.READING})

    assert not completed.is_valid()
    assert "completed_on" in completed.errors
    assert active.is_valid()


def test_completion_date_form_rejects_future_date() -> None:
    form = CompletionDateForm({"completed_on": date.today() + timedelta(days=1)})

    assert not form.is_valid()
    assert "completed_on" in form.errors
