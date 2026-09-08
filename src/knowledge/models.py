from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class KnowledgeKind(models.TextChoices):
    """Interview Context에 사용할 최소 Claim의 분류다."""

    THEME = "theme", "Theme"
    ARGUMENT = "argument", "Argument"
    CONCEPT = "concept", "Concept"
    CHARACTER = "character", "Character"
    EVENT = "event", "Event"


class BookKnowledge(models.Model):
    """특정 Book의 검증된 Context Claim 하나를 저장한다."""

    book = models.ForeignKey(
        "books.Book", on_delete=models.CASCADE, related_name="knowledge_claims"
    )
    kind = models.CharField(max_length=10, choices=KnowledgeKind.choices)
    content = models.CharField(max_length=500)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=KnowledgeKind.values),
                name="knowledge_bookknowledge_kind_valid",
            ),
            models.CheckConstraint(
                condition=Q(content__regex=r"\S"),
                name="knowledge_bookknowledge_content_not_blank",
            ),
            models.UniqueConstraint(
                fields=("book", "kind", "content"),
                name="knowledge_bookknowledge_book_kind_content_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.book} · {self.get_kind_display()}: {self.content}"

    def clean_fields(self, exclude=None) -> None:
        """필드 길이 검증 전에 Claim 양끝 공백을 정규화한다."""
        if isinstance(self.content, str):
            self.content = self.content.strip()
        super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        """정규화된 Claim이 실제 Context로 쓸 내용을 가지는지 검증한다."""
        super().clean()
        if not isinstance(self.content, str) or not self.content:
            raise ValidationError(
                {"content": "Claim 내용은 공백만으로 구성할 수 없습니다."}
            )
