import inspect
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from django.db import close_old_connections

from books import services as book_services
from books.selection_candidates import BookSelectionCandidate
from books.services import (
    BookSearchResult,
    BookSearchStatus,
    search_books,
    select_book,
)
from integrations.book_metadata.contracts import ProviderBook
from integrations.book_metadata.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class FakeProvider:
    """호출한 검색어와 미리 준비한 결과 또는 오류를 기록하는 테스트 Provider다."""

    def __init__(
        self,
        *,
        books: tuple[ProviderBook, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.books = books
        self.error = error
        self.queries: list[str] = []

    def search(self, query: str) -> tuple[ProviderBook, ...]:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.books


@pytest.fixture
def provider_books() -> tuple[ProviderBook, ProviderBook]:
    return (
        ProviderBook(
            isbn13="9788937834790",
            title="정의란 무엇인가",
            authors="마이클 샌델",
            publisher="와이즈베리",
            published_date=date(2014, 11, 20),
            cover_url="https://images.example.test/books/justice.jpg",
            description="정의에 관한 철학적 질문",
            table_of_contents="1장 옳은 일 하기",
            external_url="https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=1",
        ),
        ProviderBook(
            isbn13="9788937834791",
            title="공정하다는 착각",
            authors="마이클 샌델",
            publisher="와이즈베리",
            published_date=date(2020, 12, 1),
            cover_url="https://images.example.test/books/fairness.jpg",
            description="능력주의를 다시 생각하는 질문",
            table_of_contents="1장 승자와 패자",
            external_url="https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=2",
        ),
    )


def test_search_books_returns_preserved_success_results(
    provider_books: tuple[ProviderBook, ProviderBook],
) -> None:
    provider = FakeProvider(books=provider_books)

    result = search_books("  정의  와 공정  ", provider)

    assert provider.queries == ["정의  와 공정"]
    assert result.status is BookSearchStatus.SUCCESS
    assert result.books is provider_books
    assert result.books[0].published_date == date(2014, 11, 20)
    assert result.books[1].published_date == date(2020, 12, 1)


def test_search_books_returns_empty_for_provider_empty_result() -> None:
    provider = FakeProvider()

    result = search_books("없는 책", provider)

    assert provider.queries == ["없는 책"]
    assert result.status is BookSearchStatus.EMPTY
    assert result.books == ()


@pytest.mark.parametrize(
    ("status", "books"),
    [
        (BookSearchStatus.SUCCESS, ()),
        (
            BookSearchStatus.EMPTY,
            (
                ProviderBook(
                    isbn13="9788937834790",
                    title="정의란 무엇인가",
                    authors="",
                    publisher="",
                    published_date=None,
                    cover_url="",
                    description="",
                    table_of_contents="",
                    external_url="",
                ),
            ),
        ),
    ],
)
def test_book_search_result_rejects_invalid_status_and_books_combination(
    status: BookSearchStatus,
    books: tuple[ProviderBook, ...],
) -> None:
    with pytest.raises(ValueError):
        BookSearchResult(status=status, books=books)


@pytest.mark.parametrize(
    "error",
    [
        ProviderConfigurationError("credential must not be exposed"),
        ProviderTimeoutError("provider diagnostic detail"),
        ProviderUnavailableError("provider diagnostic detail"),
        ProviderResponseError("provider diagnostic detail"),
    ],
)
def test_search_books_returns_safe_error_for_provider_error(error: Exception) -> None:
    provider = FakeProvider(error=error)

    result = search_books("도서", provider)

    assert provider.queries == ["도서"]
    assert result.status is BookSearchStatus.ERROR
    assert result.books == ()
    assert not hasattr(result, "error")
    assert "diagnostic detail" not in repr(result)
    assert "credential" not in repr(result)


@pytest.mark.parametrize("query", ["", " \t\n "])
def test_search_books_skips_blank_query(query: str) -> None:
    provider = FakeProvider()

    result = search_books(query, provider)

    assert provider.queries == []
    assert result.status is BookSearchStatus.EMPTY
    assert result.books == ()


def test_search_books_propagates_unexpected_error() -> None:
    provider = FakeProvider(error=RuntimeError("unexpected programming error"))

    with pytest.raises(RuntimeError, match="unexpected programming error"):
        search_books("도서", provider)

    assert provider.queries == ["도서"]


def test_search_service_keeps_provider_io_outside_the_orm_boundary() -> None:
    source = inspect.getsource(book_services.search_books)

    assert "Book.objects" not in source
    assert "transaction.atomic" not in source


@pytest.mark.django_db
def test_select_book_creates_from_candidate_and_preserves_missing_metadata() -> None:
    candidate = BookSelectionCandidate(
        candidate_id="candidate",
        owner_user_id="1",
        created_at=0,
        book=ProviderBook(
            isbn13="9788937834790",
            title="정의란 무엇인가",
            authors="",
            publisher="",
            published_date=None,
            cover_url="",
            description="",
            table_of_contents="",
            external_url="",
        ),
    )

    result = select_book(candidate)

    assert result.created is True
    assert result.book.isbn13 == "9788937834790"
    assert result.book.authors == ""
    assert result.book.published_date is None


@pytest.mark.django_db
def test_select_book_reuses_existing_book_without_overwriting_metadata() -> None:
    from books.models import Book

    existing = Book.objects.create(
        isbn13="9788937834790",
        title="기존 제목",
        authors="기존 저자",
    )
    candidate = BookSelectionCandidate(
        candidate_id="candidate",
        owner_user_id="1",
        created_at=0,
        book=ProviderBook(
            isbn13=existing.isbn13,
            title="다른 제목",
            authors="다른 저자",
            publisher="",
            published_date=None,
            cover_url="",
            description="",
            table_of_contents="",
            external_url="",
        ),
    )

    first = select_book(candidate)
    second = select_book(candidate)

    existing.refresh_from_db()
    assert first.book.pk == existing.pk == second.book.pk
    assert first.created is False
    assert second.created is False
    assert existing.title == "기존 제목"
    assert existing.authors == "기존 저자"


@pytest.mark.django_db
def test_select_book_rolls_back_when_candidate_breaks_book_constraint() -> None:
    from books.models import Book

    candidate = BookSelectionCandidate(
        candidate_id="candidate",
        owner_user_id="1",
        created_at=0,
        book=ProviderBook(
            isbn13="9788937834790",
            title="",
            authors="",
            publisher="",
            published_date=None,
            cover_url="",
            description="",
            table_of_contents="",
            external_url="",
        ),
    )

    with pytest.raises(Book.DoesNotExist):
        select_book(candidate)

    assert Book.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_selection_of_same_isbn_leaves_one_book() -> None:
    from threading import Barrier

    from books.models import Book

    candidate = BookSelectionCandidate(
        candidate_id="candidate",
        owner_user_id="1",
        created_at=0,
        book=ProviderBook(
            isbn13="9788937834790",
            title="정의란 무엇인가",
            authors="",
            publisher="",
            published_date=None,
            cover_url="",
            description="",
            table_of_contents="",
            external_url="",
        ),
    )
    barrier = Barrier(2)

    def select_in_separate_connection() -> tuple[int, bool]:
        close_old_connections()
        try:
            barrier.wait()
            result = select_book(candidate)
            return result.book.pk, result.created
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: select_in_separate_connection(), range(2))
        )

    assert {book_id for book_id, _ in results} == {results[0][0]}
    assert Book.objects.filter(isbn13=candidate.book.isbn13).count() == 1
