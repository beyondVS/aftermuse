from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Interview(models.Model):
    """완독 Reading에 고정된 사용자의 생각 정리 Interview다."""

    class KnowledgeReadiness(models.TextChoices):
        READY = "READY", "준비됨"
        READY_LIMITED = "READY_LIMITED", "제한됨"

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        REFLECTION_READY = "REFLECTION_READY", "Reflection 준비 완료"
        COMPLETED = "COMPLETED", "완료"

    reading = models.OneToOneField("readings.Reading", on_delete=models.CASCADE)
    book = models.ForeignKey("books.Book", on_delete=models.PROTECT)
    knowledge_readiness = models.CharField(
        max_length=16, choices=KnowledgeReadiness.choices
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(knowledge_readiness__in=("READY", "READY_LIMITED")),
                name="reflections_interview_readiness_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=("IN_PROGRESS", "REFLECTION_READY", "COMPLETED")
                ),
                name="reflections_interview_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.book} · {self.get_status_display()}"

    def save(self, *args, **kwargs) -> None:
        """직접 저장 경로에서도 확정된 관계의 변경을 차단한다."""
        self.clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """기존 Interview의 Reading과 Book 관계 변경을 막는다."""
        super().clean()
        if self.pk is None:
            return
        original = type(self).objects.only("reading_id", "book_id").get(pk=self.pk)
        errors: dict[str, str] = {}
        if self.reading_id != original.reading_id:
            errors["reading"] = "시작된 Interview의 Reading은 변경할 수 없습니다."
        if self.book_id != original.book_id:
            errors["book"] = "시작된 Interview의 Book은 변경할 수 없습니다."
        if errors:
            raise ValidationError(errors)


class InterviewTurn(models.Model):
    """Interview 안에서 순서가 보장되는 질문과 선택적 답변이다."""

    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, db_index=False, related_name="turns"
    )
    sequence = models.PositiveIntegerField()
    question = models.CharField(max_length=2000)
    answer = models.TextField(null=True, blank=True)  # noqa: DJ001
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sequence", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(sequence__gte=1),
                name="reflections_turn_sequence_positive",
            ),
            models.CheckConstraint(
                condition=Q(question__regex=r"\S"),
                name="reflections_turn_question_not_blank",
            ),
            models.UniqueConstraint(
                fields=("interview", "sequence"),
                name="reflections_turn_interview_sequence_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.interview} · {self.sequence}"

    def clean_fields(self, exclude=None) -> None:
        """질문 길이 검증 전에 양끝 공백을 정규화한다."""
        if isinstance(self.question, str):
            self.question = self.question.strip()
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        """질문과 최초 확정 답변의 애플리케이션 계약을 검증한다."""
        super().clean()
        if not isinstance(self.question, str) or not self.question:
            raise ValidationError({"question": "질문은 공백만으로 구성할 수 없습니다."})
        if self.answer is not None:
            if (
                not isinstance(self.answer, str)
                or not self.answer.strip()
                or len(self.answer) > 2000
            ):
                raise ValidationError({"answer": "답변은 1~2,000자여야 합니다."})
        if self.pk is not None:
            original_answer = type(self).objects.only("answer").get(pk=self.pk).answer
            if original_answer is not None and self.answer != original_answer:
                raise ValidationError({"answer": "확정된 답변은 변경할 수 없습니다."})
