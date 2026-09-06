from dataclasses import dataclass
from enum import StrEnum

from django.db import IntegrityError, transaction

from books.models import Book
from books.selection_candidates import BookSelectionCandidate
from integrations.book_metadata.contracts import BookMetadataProvider, ProviderBook
from integrations.book_metadata.exceptions import ProviderError


class BookSearchStatus(StrEnum):
    """도서 검색 요청의 정규화된 완료 상태를 나타낸다."""

    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class BookSearchResult:
    """Provider 세부사항을 노출하지 않는 불변 검색 결과다."""

    status: BookSearchStatus
    books: tuple[ProviderBook, ...]

    def __post_init__(self) -> None:
        if self.status is BookSearchStatus.SUCCESS and not self.books:
            raise ValueError("SUCCESS 검색 결과에는 도서가 하나 이상 필요합니다.")
        if self.status is not BookSearchStatus.SUCCESS and self.books:
            raise ValueError(
                "EMPTY 또는 ERROR 검색 결과에는 도서를 포함할 수 없습니다."
            )


def search_books(query: str, provider: BookMetadataProvider) -> BookSearchResult:
    """검색어를 정규화해 Provider 결과를 안전한 상태와 함께 반환한다.

    ProviderError만 외부 소비자가 처리 가능한 ERROR 상태로 격리한다. 그 밖의 예외는
    프로그래밍 결함을 숨기지 않도록 전파한다.
    """
    normalized_query = query.strip()
    if not normalized_query:
        return BookSearchResult(BookSearchStatus.EMPTY, ())

    try:
        books = provider.search(normalized_query)
    except ProviderError:
        return BookSearchResult(BookSearchStatus.ERROR, ())

    if not books:
        return BookSearchResult(BookSearchStatus.EMPTY, ())
    return BookSearchResult(BookSearchStatus.SUCCESS, books)


@dataclass(frozen=True, slots=True)
class BookSelectionResult:
    """후보를 기존 또는 새 Book으로 확정한 불변 결과다."""

    book: Book
    created: bool


def select_book(candidate: BookSelectionCandidate) -> BookSelectionResult:
    """검증된 후보로 Book을 멱등적으로 생성하거나 기존 Book을 반환한다."""
    defaults = {
        "title": candidate.book.title,
        "authors": candidate.book.authors,
        "publisher": candidate.book.publisher,
        "published_date": candidate.book.published_date,
        "cover_url": candidate.book.cover_url,
        "description": candidate.book.description,
        "table_of_contents": candidate.book.table_of_contents,
    }
    try:
        with transaction.atomic():
            book, created = Book.objects.get_or_create(
                isbn13=candidate.book.isbn13,
                defaults=defaults,
            )
    except IntegrityError:
        book = Book.objects.get(isbn13=candidate.book.isbn13)
        created = False
    return BookSelectionResult(book=book, created=created)
