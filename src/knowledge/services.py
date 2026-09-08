import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from books.models import Book
from knowledge.models import BookKnowledge, KnowledgeKind

ISBN13_PATTERN = re.compile(r"[0-9]{13}\Z")


class BookKnowledgeReadiness(StrEnum):
    """후속 Interview가 선택할 Book Context 준비 수준이다."""

    READY = "READY"
    READY_LIMITED = "READY_LIMITED"


@dataclass(frozen=True, slots=True)
class BookKnowledgeCreationResult:
    """Claim 등록 결과와 이번 호출의 신규 생성 여부다."""

    book_knowledge: BookKnowledge
    created: bool


@dataclass(frozen=True, slots=True)
class BookKnowledgeSeedResult:
    """Seed 적용에서 새로 만든 Claim과 재사용한 Claim의 수다."""

    created: int
    reused: int


def create_book_knowledge(
    *, book: Book, kind: str, content: str
) -> BookKnowledgeCreationResult:
    """정규화된 Claim을 멱등 등록하고 동시 중복은 기존 행으로 복구한다."""
    _validate_saved_book(book)
    normalized_kind = _normalize_kind(kind)
    normalized_content = _normalize_content(content)
    existing = BookKnowledge.objects.filter(
        book=book, kind=normalized_kind, content=normalized_content
    ).first()
    if existing is not None:
        return BookKnowledgeCreationResult(existing, created=False)

    claim = BookKnowledge(book=book, kind=normalized_kind, content=normalized_content)
    try:
        with transaction.atomic():
            claim.full_clean(validate_unique=False, validate_constraints=False)
            claim.save(force_insert=True)
    except IntegrityError as error:
        existing = BookKnowledge.objects.filter(
            book=book, kind=normalized_kind, content=normalized_content
        ).first()
        if existing is None:
            raise error
        return BookKnowledgeCreationResult(existing, created=False)
    return BookKnowledgeCreationResult(claim, created=True)


def list_book_knowledge(book: Book) -> list[BookKnowledge]:
    """한 Book의 Claim만 Context 재현 가능한 순서로 반환한다."""
    return list(BookKnowledge.objects.filter(book=book).order_by("kind", "id"))


def get_book_knowledge_readiness(book: Book) -> BookKnowledgeReadiness:
    """현재 Claim 존재 여부에서 Book 준비 상태를 저장 없이 계산한다."""
    if BookKnowledge.objects.filter(book=book).exists():
        return BookKnowledgeReadiness.READY
    return BookKnowledgeReadiness.READY_LIMITED


def seed_book_knowledge(
    entries: Sequence[Mapping[str, object]],
) -> BookKnowledgeSeedResult:
    """모든 Seed를 선검증한 뒤 하나의 transaction으로 멱등 적용한다."""
    normalized_entries = _normalize_seed_entries(entries)
    books_by_isbn13 = Book.objects.in_bulk(
        {isbn13 for isbn13, _kind, _content in normalized_entries}, field_name="isbn13"
    )
    missing_isbn13 = sorted(
        {
            isbn13
            for isbn13, _kind, _content in normalized_entries
            if isbn13 not in books_by_isbn13
        }
    )
    if missing_isbn13:
        raise ValidationError(
            {"book_isbn13": f"대상 Book이 없습니다: {', '.join(missing_isbn13)}"}
        )

    created = 0
    reused = 0
    with transaction.atomic():
        for isbn13, kind, content in normalized_entries:
            result = create_book_knowledge(
                book=books_by_isbn13[isbn13], kind=kind, content=content
            )
            if result.created:
                created += 1
            else:
                reused += 1
    return BookKnowledgeSeedResult(created=created, reused=reused)


def _validate_saved_book(book: Book) -> None:
    if not isinstance(book, Book) or book.pk is None:
        raise ValidationError({"book": "저장된 Book이 필요합니다."})


def _normalize_kind(kind: str) -> str:
    try:
        return KnowledgeKind(kind).value
    except (TypeError, ValueError) as error:
        raise ValidationError(
            {"kind": "지원하지 않는 Knowledge kind입니다."}
        ) from error


def _normalize_content(content: str) -> str:
    if not isinstance(content, str):
        raise ValidationError({"content": "Claim 내용은 문자열이어야 합니다."})
    normalized_content = content.strip()
    if not normalized_content or len(normalized_content) > 500:
        raise ValidationError({"content": "Claim 내용은 1~500자여야 합니다."})
    return normalized_content


def _normalize_seed_entries(
    entries: Sequence[Mapping[str, object]],
) -> list[tuple[str, str, str]]:
    if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence):
        raise ValidationError({"seed": "Seed 데이터는 항목 목록이어야 합니다."})
    normalized_entries: list[tuple[str, str, str]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ValidationError(
                {"seed": f"{index}번 Seed 항목 형식이 올바르지 않습니다."}
            )
        isbn13 = entry.get("book_isbn13")
        if not isinstance(isbn13, str) or not ISBN13_PATTERN.fullmatch(isbn13):
            raise ValidationError(
                {"book_isbn13": f"{index}번 ISBN13이 올바르지 않습니다."}
            )
        normalized_entries.append(
            (
                isbn13,
                _normalize_kind(entry.get("kind")),
                _normalize_content(entry.get("content")),
            )
        )
    return normalized_entries
