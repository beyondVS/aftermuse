from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderBook:
    """외부 Provider에서 검증·정규화한 도서 Metadata를 표현한다."""

    isbn13: str
    title: str
    authors: str
    publisher: str
    published_date: date | None
    cover_url: str
    description: str
    table_of_contents: str
    external_url: str


class BookMetadataProvider(Protocol):
    """Provider 중립 도서 Metadata 검색 계약이다."""

    def search(self, query: str) -> tuple[ProviderBook, ...]:
        """검색어에 해당하는 정규화된 도서 목록을 반환한다."""
