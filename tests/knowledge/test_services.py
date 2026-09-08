from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections

from books.models import Book
from knowledge.models import BookKnowledge, KnowledgeKind
from knowledge.services import (
    BookKnowledgeReadiness,
    create_book_knowledge,
    get_book_knowledge_readiness,
    list_book_knowledge,
)


def create_book(*, isbn13: str = "9780000000011") -> Book:
    """Service 테스트용 Book을 만든다."""
    return Book.objects.create(isbn13=isbn13, title="Knowledge Service 테스트 도서")


@pytest.mark.django_db
def test_create_book_knowledge_trims_and_is_idempotent() -> None:
    book = create_book()

    first = create_book_knowledge(
        book=book, kind=KnowledgeKind.THEME, content="  감시 사회  "
    )
    second = create_book_knowledge(book=book, kind="theme", content="감시 사회")

    assert first.created is True
    assert first.book_knowledge.content == "감시 사회"
    assert second.created is False
    assert second.book_knowledge.pk == first.book_knowledge.pk
    assert BookKnowledge.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "content"),
    [
        ("invalid", "유효한 Claim"),
        (KnowledgeKind.THEME, " \t "),
        (KnowledgeKind.THEME, "x" * 501),
    ],
)
def test_create_book_knowledge_rejects_invalid_input(kind: str, content: str) -> None:
    with pytest.raises(ValidationError):
        create_book_knowledge(book=create_book(), kind=kind, content=content)


@pytest.mark.django_db
def test_create_book_knowledge_rejects_unsaved_book() -> None:
    with pytest.raises(ValidationError):
        create_book_knowledge(
            book=Book(isbn13="9780000000012", title="미저장 도서"),
            kind=KnowledgeKind.THEME,
            content="유효한 Claim",
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_claim_creation_reuses_one_claim() -> None:
    book = create_book()
    barrier = Barrier(2)

    def create_from_separate_connection() -> tuple[int, bool]:
        close_old_connections()
        try:
            barrier.wait()
            result = create_book_knowledge(
                book=book, kind=KnowledgeKind.THEME, content="동시 등록 Claim"
            )
            return result.book_knowledge.pk, result.created
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: create_from_separate_connection(), range(2))
        )

    assert len({claim_id for claim_id, _created in results}) == 1
    assert sorted(created for _claim_id, created in results) == [False, True]


@pytest.mark.django_db
def test_list_book_knowledge_is_isolated_and_deterministically_ordered(
    django_assert_num_queries,
) -> None:
    book = create_book()
    other_book = create_book(isbn13="9780000000013")
    second_theme = BookKnowledge.objects.create(
        book=book, kind=KnowledgeKind.THEME, content="두 번째 Theme"
    )
    concept = BookKnowledge.objects.create(
        book=book, kind=KnowledgeKind.CONCEPT, content="Concept"
    )
    first_theme = BookKnowledge.objects.create(
        book=book, kind=KnowledgeKind.THEME, content="첫 번째 Theme"
    )
    BookKnowledge.objects.create(
        book=other_book, kind=KnowledgeKind.ARGUMENT, content="다른 책 Claim"
    )

    with django_assert_num_queries(1):
        claims = list_book_knowledge(book)

    assert [claim.pk for claim in claims] == [
        concept.pk,
        second_theme.pk,
        first_theme.pk,
    ]
    assert all(claim.book_id == book.pk for claim in claims)


@pytest.mark.django_db
def test_readiness_is_derived_per_book_without_persistence_side_effect(
    django_assert_num_queries,
) -> None:
    ready_book = create_book()
    limited_book = create_book(isbn13="9780000000014")
    BookKnowledge.objects.create(
        book=ready_book, kind=KnowledgeKind.ARGUMENT, content="준비된 Claim"
    )

    with django_assert_num_queries(1):
        ready = get_book_knowledge_readiness(ready_book)
    with django_assert_num_queries(1):
        limited = get_book_knowledge_readiness(limited_book)

    assert ready is BookKnowledgeReadiness.READY
    assert limited is BookKnowledgeReadiness.READY_LIMITED
    assert BookKnowledge.objects.filter(book=ready_book).count() == 1
