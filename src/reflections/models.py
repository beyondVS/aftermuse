from enum import StrEnum

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL


class CoreCoverageAxis(StrEnum):
    """Reflection 근거를 수집하는 고정 Coverage 축이다."""

    MEMORY = "MEMORY"
    REACTION = "REACTION"
    CONNECTION = "CONNECTION"
    AFTERTHOUGHT = "AFTERTHOUGHT"


class CoverageStatus(StrEnum):
    """Core Coverage 축의 단방향 수집 상태다."""

    UNCOVERED = "UNCOVERED"
    PARTIAL = "PARTIAL"
    COVERED = "COVERED"


CORE_COVERAGE = tuple(CoreCoverageAxis)
COVERAGE_AXES_SQL = "ARRAY['MEMORY', 'REACTION', 'CONNECTION', 'AFTERTHOUGHT']"
COVERAGE_CONSTRAINT_SQL = f"""
jsonb_typeof(coverage) = 'object'
AND (coverage - {COVERAGE_AXES_SQL}::text[]) = '{{}}'::jsonb
AND coverage ?& {COVERAGE_AXES_SQL}
AND (coverage->>'MEMORY') IN ('UNCOVERED', 'PARTIAL', 'COVERED')
AND (coverage->>'REACTION') IN ('UNCOVERED', 'PARTIAL', 'COVERED')
AND (coverage->>'CONNECTION') IN ('UNCOVERED', 'PARTIAL', 'COVERED')
AND (coverage->>'AFTERTHOUGHT') IN ('UNCOVERED', 'PARTIAL', 'COVERED')
""".strip()


def default_coverage() -> dict[str, str]:
    """새 Interview에 독립적인 canonical Coverage 값을 제공한다."""
    return {axis.value: CoverageStatus.UNCOVERED.value for axis in CORE_COVERAGE}


def is_canonical_coverage(value: object) -> bool:
    """저장 가능한 Coverage JSON object shape인지 확인한다."""
    return (
        isinstance(value, dict)
        and set(value) == {axis.value for axis in CORE_COVERAGE}
        and all(
            isinstance(status, str)
            and status in {item.value for item in CoverageStatus}
            for status in value.values()
        )
    )


class Interview(models.Model):
    """완독 Reading에 고정된 사용자의 생각 정리 Interview다."""

    class KnowledgeReadiness(models.TextChoices):
        READY = "READY", "준비됨"
        READY_LIMITED = "READY_LIMITED", "제한됨"

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        REFLECTION_READY = "REFLECTION_READY", "Reflection 준비 완료"
        COMPLETED = "COMPLETED", "완료"
        ENDED_NO_REFLECTION = "ENDED_NO_REFLECTION", "답변 부족 종결"

    reading = models.OneToOneField("readings.Reading", on_delete=models.CASCADE)
    book = models.ForeignKey("books.Book", on_delete=models.PROTECT)
    knowledge_readiness = models.CharField(
        max_length=16, choices=KnowledgeReadiness.choices
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    coverage = models.JSONField(
        default=default_coverage,
        db_default=models.Value(default_coverage(), output_field=models.JSONField()),
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
                    status__in=(
                        "IN_PROGRESS",
                        "REFLECTION_READY",
                        "COMPLETED",
                        "ENDED_NO_REFLECTION",
                    )
                ),
                name="reflections_interview_status_valid",
            ),
            models.CheckConstraint(
                condition=RawSQL(
                    COVERAGE_CONSTRAINT_SQL,
                    params=(),
                    output_field=models.BooleanField(),
                ),
                name="reflections_interview_coverage_canonical",
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
        if not is_canonical_coverage(self.coverage):
            raise ValidationError({"coverage": "Coverage 형식이 올바르지 않습니다."})
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
    user_skipped_at = models.DateTimeField(null=True, blank=True)
    next_question_skipped_at = models.DateTimeField(null=True, blank=True)
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
            models.CheckConstraint(
                condition=Q(answer__isnull=True) | Q(user_skipped_at__isnull=True),
                name="reflections_turn_result_mutually_exclusive",
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
        """질문과 최초 확정 답변 및 건너뛰기의 애플리케이션 계약을 검증한다."""
        super().clean()
        if not isinstance(self.question, str) or not self.question:
            raise ValidationError({"question": "질문은 공백만으로 구성할 수 없습니다."})
        if self.answer is not None and self.user_skipped_at is not None:
            raise ValidationError(
                {"answer": "답변과 건너뛰기를 동시에 설정할 수 없습니다."}
            )
        if self.answer is not None:
            if (
                not isinstance(self.answer, str)
                or not self.answer.strip()
                or len(self.answer) > 2000
            ):
                raise ValidationError({"answer": "답변은 1~2,000자여야 합니다."})
        if self.next_question_skipped_at is not None and self.answer is None:
            raise ValidationError(
                {"next_question_skipped_at": "확정된 답변이 필요합니다."}
            )
        if self.pk is not None:
            self._validate_persisted_turn_immutability()

    def _validate_persisted_turn_immutability(self) -> None:
        """이미 저장된 Turn의 확정 답변 및 건너뛰기 불변성을 검증한다."""
        original = type(self).objects.only("answer", "user_skipped_at").get(pk=self.pk)
        if original.answer is not None and self.answer != original.answer:
            raise ValidationError({"answer": "확정된 답변은 변경할 수 없습니다."})
        if original.answer is not None and self.user_skipped_at is not None:
            raise ValidationError(
                {"user_skipped_at": "확정된 답변이 있는 질문은 건너뛸 수 없습니다."}
            )
        if (
            original.user_skipped_at is not None
            and self.user_skipped_at != original.user_skipped_at
        ):
            raise ValidationError(
                {"user_skipped_at": "건너뛴 시각은 변경할 수 없습니다."}
            )
        if original.user_skipped_at is not None and self.answer is not None:
            raise ValidationError(
                {"answer": "이미 건너뛴 질문에는 답변을 작성할 수 없습니다."}
            )


class InterviewProgressDecision(models.Model):
    """확정 답변 뒤 보류한 다음 질문과 사용자의 진행 선택이다."""

    class Kind(models.TextChoices):
        SOFT_STOP = "SOFT_STOP", "조기 마무리 선택"
        CAP_EXTENSION = "CAP_EXTENSION", "질문 상한 연장 선택"

    class Selection(models.TextChoices):
        END = "END", "마치기"
        CONTINUE = "CONTINUE", "계속하기"

    turn = models.OneToOneField(
        InterviewTurn, on_delete=models.CASCADE, related_name="progress_decision"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    selection = models.CharField(  # noqa: DJ001
        max_length=8, choices=Selection.choices, null=True, blank=True
    )
    candidate_question = models.CharField(max_length=300)
    candidate_focus_axis = models.CharField(  # noqa: DJ001
        max_length=16,
        choices=[(axis.value, axis.value) for axis in CoreCoverageAxis],
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=("SOFT_STOP", "CAP_EXTENSION")),
                name="reflections_progress_kind_valid",
            ),
            models.CheckConstraint(
                condition=Q(selection__isnull=True)
                | Q(selection__in=("END", "CONTINUE")),
                name="reflections_progress_selection_valid",
            ),
            models.CheckConstraint(
                condition=(Q(selection__isnull=True) & Q(decided_at__isnull=True))
                | (Q(selection__isnull=False) & Q(decided_at__isnull=False)),
                name="reflections_progress_decided_consistent",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.turn} · {self.kind}"

    def clean(self) -> None:
        """대기 질문과 결정 시점의 애플리케이션 불변식을 확인한다."""
        super().clean()
        if self.turn_id and self.turn.answer is None:
            raise ValidationError({"turn": "확정된 답변이 필요합니다."})
        if (
            not isinstance(self.candidate_question, str)
            or not self.candidate_question.strip()
        ):
            raise ValidationError({"candidate_question": "질문 후보가 필요합니다."})


_DRAFT_MARKDOWN_CONSTRAINT_SQL = (
    "char_length(draft_markdown) >= 1 "
    "AND char_length(draft_markdown) <= 22000 "
    "AND length(trim(draft_markdown)) > 0"
)
_REVISED_MARKDOWN_CONSTRAINT_SQL = (
    "revised_markdown IS NULL OR ("
    "char_length(revised_markdown) >= 1 "
    "AND char_length(revised_markdown) <= 20000 "
    "AND length(trim(revised_markdown)) > 0"
    ")"
)
_SECTIONS_ARRAY_CONSTRAINT_SQL = "jsonb_typeof(draft_sections) = 'array'"


class Reflection(models.Model):
    """Interview 완독 후 확정된 생각으로 구성된 독서노트 초안 및 수정본이다."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "초안"

    id = models.BigAutoField(primary_key=True)
    interview = models.OneToOneField(
        Interview, on_delete=models.CASCADE, related_name="reflection"
    )
    draft_markdown = models.TextField()
    draft_sections = models.JSONField()
    revised_markdown = models.TextField(null=True, blank=True)  # noqa: DJ001
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status="DRAFT"),
                name="reflections_reflection_status_draft",
            ),
            models.CheckConstraint(
                condition=Q(completed_at__isnull=True),
                name="reflections_reflection_completed_at_null",
            ),
            models.CheckConstraint(
                condition=RawSQL(
                    _DRAFT_MARKDOWN_CONSTRAINT_SQL,
                    params=(),
                    output_field=models.BooleanField(),
                ),
                name="reflections_reflection_draft_markdown_valid",
            ),
            models.CheckConstraint(
                condition=RawSQL(
                    _REVISED_MARKDOWN_CONSTRAINT_SQL,
                    params=(),
                    output_field=models.BooleanField(),
                ),
                name="reflections_reflection_revised_markdown_valid",
            ),
            models.CheckConstraint(
                condition=RawSQL(
                    _SECTIONS_ARRAY_CONSTRAINT_SQL,
                    params=(),
                    output_field=models.BooleanField(),
                ),
                name="reflections_reflection_draft_sections_array",
            ),
        ]

    def __str__(self) -> str:
        return f"Reflection({self.interview_id}) · {self.status}"

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def _validate_markdown_fields(self) -> None:
        """초안 및 수정본 Markdown의 타입과 길이 제약을 검증한다."""
        if not isinstance(self.draft_markdown, str) or isinstance(
            self.draft_markdown, bool
        ):
            raise ValidationError(
                {"draft_markdown": "초안 본문은 문자열이어야 합니다."}
            )
        if not self.draft_markdown.strip():
            raise ValidationError(
                {"draft_markdown": "초안 본문은 공백만으로 구성될 수 없습니다."}
            )
        if len(self.draft_markdown) < 1 or len(self.draft_markdown) > 22000:
            raise ValidationError(
                {"draft_markdown": "초안 본문 길이는 1–22,000자여야 합니다."}
            )

        if self.revised_markdown is not None:
            if not isinstance(self.revised_markdown, str) or isinstance(
                self.revised_markdown, bool
            ):
                raise ValidationError(
                    {"revised_markdown": "수정본은 문자열 또는 None이어야 합니다."}
                )
            if not self.revised_markdown.strip():
                raise ValidationError(
                    {"revised_markdown": "수정본은 공백만으로 구성될 수 없습니다."}
                )
            if len(self.revised_markdown) > 20000:
                raise ValidationError(
                    {"revised_markdown": "수정본 길이는 20,000자를 초과할 수 없습니다."}
                )

    def _validate_sections(self) -> None:
        """draft_sections의 JSON 배열 구조를 검증한다."""
        if not isinstance(self.draft_sections, list) or isinstance(
            self.draft_sections, (str, bytes)
        ):
            raise ValidationError(
                {"draft_sections": "draft_sections는 JSON 배열이어야 합니다."}
            )

    def _validate_immutability(self) -> None:
        """기존 인스턴스의 interview, draft 본문 및 섹션 불변성을 강제한다."""
        if not self.pk:
            return
        original = Reflection.objects.filter(pk=self.pk).first()
        if not original:
            return
        if self.interview_id != original.interview_id:
            raise ValidationError({"interview": "Interview 관계는 변경할 수 없습니다."})
        if self.draft_markdown != original.draft_markdown:
            raise ValidationError(
                {"draft_markdown": "최초 초안 본문은 변경할 수 없습니다."}
            )
        if self.draft_sections != original.draft_sections:
            raise ValidationError(
                {"draft_sections": "최초 초안 섹션은 변경할 수 없습니다."}
            )

    def clean(self) -> None:
        super().clean()
        if self.status != self.Status.DRAFT:
            raise ValidationError({"status": "Day 10에서는 DRAFT 상태만 허용됩니다."})
        if self.completed_at is not None:
            raise ValidationError(
                {"completed_at": "Day 10에서는 완료 시각을 지정할 수 없습니다."}
            )
        self._validate_markdown_fields()
        self._validate_sections()
        self._validate_immutability()
