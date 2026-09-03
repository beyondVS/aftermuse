from dataclasses import dataclass
from enum import StrEnum

from integrations.aladin.contracts import BookMetadataProvider, ProviderBook
from integrations.aladin.exceptions import ProviderError


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
