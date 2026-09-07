from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Reading(models.Model):
    """한 사용자가 특정 책을 읽은 한 번의 경험을 나타낸다."""

    class Status(models.TextChoices):
        WANT_TO_READ = "want_to_read", "읽고 싶음"
        READING = "reading", "읽는 중"
        COMPLETED = "completed", "완독"

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    book = models.ForeignKey("books.Book", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices)
    completed_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status="completed", completed_on__isnull=False)
                    | (~Q(status="completed") & Q(completed_on__isnull=True))
                ),
                name="readings_completion_date_state",
            ),
            models.UniqueConstraint(
                fields=("user", "book"),
                condition=Q(status__in=("want_to_read", "reading")),
                name="readings_active_user_book_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.book} · {self.get_status_display()}"

    def clean(self) -> None:
        """상태와 완독일이 함께 유지해야 하는 도메인 규칙을 검증한다."""
        super().clean()
        errors: dict[str, str] = {}
        if self.status == self.Status.COMPLETED:
            if self.completed_on is None:
                errors["completed_on"] = "완독 상태에는 완독일이 필요합니다."
            elif self.completed_on > date.today():
                errors["completed_on"] = "완독일은 오늘 이후로 지정할 수 없습니다."
        elif self.completed_on is not None:
            errors["completed_on"] = "완독이 아닌 상태에는 완독일을 지정할 수 없습니다."
        if errors:
            raise ValidationError(errors)

    @property
    def is_active(self) -> bool:
        """현재 Reading이 진행 중인 유일성 대상인지 반환한다."""
        return self.status in {self.Status.WANT_TO_READ, self.Status.READING}
