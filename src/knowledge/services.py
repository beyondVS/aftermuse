import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from books.models import Book
from knowledge.models import BookKnowledge, KnowledgeKind

ISBN13_PATTERN = re.compile(r"[0-9]{13}\Z")

VALIDATION_BOOKS_PATH = (
    Path(__file__).resolve().parent / "seed_data" / "validation_books.json"
)
BOOK_KNOWLEDGE_SEED_PATH = (
    Path(__file__).resolve().parent / "seed_data" / "book_knowledge.json"
)


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


@dataclass(frozen=True, slots=True)
class ValidationBooksPreparationResult:
    """검증 도서 세트 준비 결과 (생성/재사용 Book 수 및 Claim 수)."""

    books_created: int
    books_reused: int
    claims_created: int
    claims_reused: int


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


def _validate_single_validation_descriptor(idx: int, desc: Any) -> None:
    if not isinstance(desc, dict):
        raise ValidationError(f"{idx}번 descriptor 형식이 올바르지 않습니다.")
    isbn13 = desc.get("isbn13")
    if not isinstance(isbn13, str) or not ISBN13_PATTERN.fullmatch(isbn13):
        raise ValidationError(
            f"{idx}번 descriptor의 ISBN13이 올바르지 않습니다: {isbn13}"
        )
    title = desc.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValidationError(f"{idx}번 descriptor의 title이 올바르지 않습니다.")
    authors = desc.get("authors")
    if not isinstance(authors, str) or not authors.strip():
        raise ValidationError(f"{idx}번 descriptor의 authors가 올바르지 않습니다.")
    genre = desc.get("genre")
    if genre not in ("fiction", "nonfiction"):
        raise ValidationError(
            f"{idx}번 descriptor의 genre가 올바르지 않습니다: {genre}"
        )
    readiness = desc.get("expected_readiness")
    if readiness not in ("READY", "READY_LIMITED"):
        raise ValidationError(
            f"{idx}번 descriptor의 expected_readiness가 올바르지 않습니다: {readiness}"
        )


def _load_and_validate_validation_descriptors(path: Path) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as f:
            descriptors = json.load(f)
    except (OSError, json.JSONDecodeError) as err:
        raise ValidationError(
            f"검증 도서 descriptor JSON을 읽을 수 없습니다: {err}"
        ) from err

    if not isinstance(descriptors, list) or len(descriptors) != 3:
        raise ValidationError("검증 도서 descriptor는 정확히 3개의 항목이어야 합니다.")

    for idx, desc in enumerate(descriptors):
        _validate_single_validation_descriptor(idx, desc)

    isbns = [desc["isbn13"] for desc in descriptors]
    if len(set(isbns)) != 3:
        raise ValidationError("검증 도서 descriptor의 ISBN13은 서로 달라야 합니다.")

    ready_fiction = sum(
        1
        for d in descriptors
        if d.get("expected_readiness") == "READY" and d.get("genre") == "fiction"
    )
    ready_nonfiction = sum(
        1
        for d in descriptors
        if d.get("expected_readiness") == "READY" and d.get("genre") == "nonfiction"
    )
    ready_limited_fiction = sum(
        1
        for d in descriptors
        if d.get("expected_readiness") == "READY_LIMITED"
        and d.get("genre") == "fiction"
    )

    if ready_fiction != 1 or ready_nonfiction != 1 or ready_limited_fiction != 1:
        raise ValidationError(
            "검증 도서 세트는 정확히 READY 소설 1권, READY 비문학 1권, "
            "READY_LIMITED 소설 1권이어야 합니다."
        )

    return descriptors


def _validate_seed_claims_for_validation_books(
    descriptors: list[dict[str, Any]],
    seed_claims: Any,
) -> list[tuple[str, str, str]]:
    """검증 도서 세트용 승인 Seed Claim 목록을 DB 쓰기 전에 검증한다."""
    normalized_entries = _normalize_seed_entries(seed_claims)
    if len(normalized_entries) != 8:
        raise ValidationError(
            f"승인 Seed Claim은 정확히 8개여야 합니다 "
            f"(현재 {len(normalized_entries)}개)."
        )

    ready_isbns = {
        desc["isbn13"]
        for desc in descriptors
        if desc.get("expected_readiness") == BookKnowledgeReadiness.READY.value
    }
    claim_isbns = {entry[0] for entry in normalized_entries}

    unknown_isbns = claim_isbns - ready_isbns
    if unknown_isbns:
        formatted = sorted(unknown_isbns)
        raise ValidationError(
            f"승인 Seed Claim에 READY 도서가 아닌 ISBN이 포함되어 있습니다: {formatted}"
        )

    missing_isbns = ready_isbns - claim_isbns
    if missing_isbns:
        formatted = sorted(missing_isbns)
        raise ValidationError(
            f"승인 Seed Claim에 일부 READY 도서의 Claim이 누락되었습니다: {formatted}"
        )

    return normalized_entries


def prepare_validation_books(
    descriptor_path: Path | None = None,
    seed_path: Path | None = None,
) -> ValidationBooksPreparationResult:
    """검증 도서 3권과 승인 Claim을 원자적으로 준비한다."""
    desc_file = descriptor_path or VALIDATION_BOOKS_PATH
    claims_file = seed_path or BOOK_KNOWLEDGE_SEED_PATH

    descriptors = _load_and_validate_validation_descriptors(desc_file)

    try:
        with open(claims_file, encoding="utf-8") as f:
            raw_seed_claims = json.load(f)
    except (OSError, json.JSONDecodeError) as err:
        raise ValidationError(
            f"승인 Seed Claim JSON을 읽을 수 없습니다: {err}"
        ) from err

    normalized_claims = _validate_seed_claims_for_validation_books(
        descriptors, raw_seed_claims
    )

    books_created = 0
    books_reused = 0
    claims_created = 0
    claims_reused = 0

    with transaction.atomic():
        # 1. LIMITED 대상 도서에 기존 Claim이 있는지 검사 (있으면 rollback 및 거부)
        for desc in descriptors:
            if desc["expected_readiness"] == BookKnowledgeReadiness.READY_LIMITED.value:
                existing_book = Book.objects.filter(isbn13=desc["isbn13"]).first()
                if (
                    existing_book is not None
                    and BookKnowledge.objects.filter(book=existing_book).exists()
                ):
                    raise ValidationError(
                        f"READY_LIMITED 대상 도서({existing_book.title})에 "
                        "이미 Knowledge Claim이 존재합니다."
                    )

        # 2. 3권 Book get_or_create (기존 서지정보 보존)
        books_map: dict[str, Book] = {}
        for desc in descriptors:
            book, created = Book.objects.get_or_create(
                isbn13=desc["isbn13"],
                defaults={
                    "title": desc["title"],
                    "authors": desc["authors"],
                },
            )
            books_map[desc["isbn13"]] = book
            if created:
                books_created += 1
            else:
                books_reused += 1

        # 3. READY 대상 도서에 승인 Claim 적용
        for isbn13, kind, content in normalized_claims:
            book = books_map[isbn13]
            claim_res = create_book_knowledge(
                book=book,
                kind=kind,
                content=content,
            )
            if claim_res.created:
                claims_created += 1
            else:
                claims_reused += 1

    return ValidationBooksPreparationResult(
        books_created=books_created,
        books_reused=books_reused,
        claims_created=claims_created,
        claims_reused=claims_reused,
    )
