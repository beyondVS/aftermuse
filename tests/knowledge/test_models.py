import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from books.models import Book
from knowledge.models import BookKnowledge, KnowledgeKind


def create_book(*, isbn13: str = "9780000000001") -> Book:
    """Knowledge 테스트에 필요한 저장된 Book을 만든다."""
    return Book.objects.create(isbn13=isbn13, title="Knowledge 테스트 도서")


@pytest.mark.django_db
def test_book_knowledge_persists_each_supported_kind() -> None:
    book = create_book()

    claims = [
        BookKnowledge.objects.create(book=book, kind=kind, content=f"{kind} Claim")
        for kind in KnowledgeKind.values
    ]

    assert {claim.kind for claim in claims} == set(KnowledgeKind.values)
    assert {claim.book_id for claim in claims} == {book.pk}


@pytest.mark.django_db
@pytest.mark.parametrize("content", ["", " \t\n "])
def test_book_knowledge_full_clean_rejects_blank_content(content: str) -> None:
    claim = BookKnowledge(book=create_book(), kind=KnowledgeKind.THEME, content=content)

    with pytest.raises(ValidationError):
        claim.full_clean()


@pytest.mark.django_db
def test_book_knowledge_full_clean_trims_content_and_enforces_max_length() -> None:
    book = create_book()
    claim = BookKnowledge(
        book=book, kind=KnowledgeKind.CONCEPT, content="  유지할 내용  "
    )

    claim.full_clean()

    assert claim.content == "유지할 내용"
    with pytest.raises(ValidationError):
        BookKnowledge(
            book=book,
            kind=KnowledgeKind.CONCEPT,
            content="x" * 501,
        ).full_clean()


@pytest.mark.django_db(transaction=True)
def test_book_knowledge_database_constraints_reject_invalid_values() -> None:
    book = create_book()

    for kind, content in (("invalid", "유효한 Claim"), (KnowledgeKind.THEME, " \t ")):
        with pytest.raises(IntegrityError), transaction.atomic():
            BookKnowledge.objects.create(book=book, kind=kind, content=content)


@pytest.mark.django_db(transaction=True)
def test_book_knowledge_unique_constraint_is_scoped_to_book_kind_and_content() -> None:
    book = create_book()
    other_book = create_book(isbn13="9780000000002")
    BookKnowledge.objects.create(book=book, kind=KnowledgeKind.THEME, content="감시")

    with pytest.raises(IntegrityError), transaction.atomic():
        BookKnowledge.objects.create(
            book=book, kind=KnowledgeKind.THEME, content="감시"
        )

    BookKnowledge.objects.create(book=book, kind=KnowledgeKind.CONCEPT, content="감시")
    BookKnowledge.objects.create(
        book=other_book, kind=KnowledgeKind.THEME, content="감시"
    )

    assert BookKnowledge.objects.count() == 3
