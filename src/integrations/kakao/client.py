"""Kakao 도서 검색 API를 중립 Provider 계약으로 변환한다."""

import json
from collections.abc import Callable
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from integrations.book_metadata.contracts import ProviderBook
from integrations.book_metadata.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

KAKAO_BOOK_SEARCH_ENDPOINT = "https://dapi.kakao.com/v3/search/book"
DEFAULT_TIMEOUT_SECONDS = 3.0
Transport = Callable[[Request, float], bytes]


def _urlopen_transport(request: Request, timeout: float) -> bytes:
    """표준 라이브러리 transport로 요청 본문을 읽는다."""
    with urlopen(request, timeout=timeout) as response:
        return response.read()


class KakaoBookMetadataProvider:
    """Kakao 검색 응답을 선택 가능한 중립 도서 Metadata로 정규화한다."""

    def __init__(
        self,
        rest_api_key: str,
        *,
        transport: Transport = _urlopen_transport,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._rest_api_key = rest_api_key.strip()
        self._transport = transport
        self._timeout = timeout

    def search(self, query: str) -> tuple[ProviderBook, ...]:
        """Kakao에서 유효한 ISBN13과 제목을 가진 결과만 반환한다."""
        if not self._rest_api_key:
            raise ProviderConfigurationError

        try:
            payload = self._transport(self._build_request(query), self._timeout)
        except TimeoutError as error:
            raise ProviderTimeoutError from error
        except HTTPError as error:
            raise ProviderUnavailableError from error
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ProviderTimeoutError from error
            raise ProviderUnavailableError from error
        except OSError as error:
            raise ProviderUnavailableError from error

        data = self._decode_payload(payload)
        documents = data.get("documents")
        if not isinstance(documents, list):
            raise ProviderResponseError

        books: list[ProviderBook] = []
        for document in documents:
            book = self._parse_document(document)
            if book is not None:
                books.append(book)
        return tuple(books)

    def _build_request(self, query: str) -> Request:
        """Secret을 header에만 둔 Kakao 검색 GET 요청을 구성한다."""
        parameters = urlencode(
            {"query": query, "sort": "accuracy", "page": "1", "size": "20"}
        )
        return Request(
            f"{KAKAO_BOOK_SEARCH_ENDPOINT}?{parameters}",
            headers={"Authorization": f"KakaoAK {self._rest_api_key}"},
            method="GET",
        )

    @staticmethod
    def _decode_payload(payload: bytes) -> dict[str, object]:
        """응답을 JSON object로만 해석한다."""
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProviderResponseError from error
        if not isinstance(data, dict):
            raise ProviderResponseError
        return data

    @staticmethod
    def _parse_document(document: object) -> ProviderBook | None:
        """문서 구조를 검증하고 필수값이 없는 항목은 제외한다."""
        if not isinstance(document, dict):
            raise ProviderResponseError

        isbn13 = _find_isbn13(document.get("isbn"))
        title = _text(document.get("title"))
        if not isbn13 or not title:
            return None

        authors = document.get("authors")
        if authors is not None and not isinstance(authors, list):
            raise ProviderResponseError
        if isinstance(authors, list) and any(
            not isinstance(author, str) for author in authors
        ):
            raise ProviderResponseError

        return ProviderBook(
            isbn13=isbn13,
            title=title,
            authors=", ".join(author.strip() for author in authors if author.strip())
            if isinstance(authors, list)
            else "",
            publisher=_text(document.get("publisher")),
            published_date=_parse_iso_date(document.get("datetime")),
            cover_url=_text(document.get("thumbnail")),
            description=_text(document.get("contents")),
            table_of_contents="",
            external_url=_text(document.get("url")),
        )


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _find_isbn13(value: object) -> str:
    """공백·하이픈으로 구분된 ISBN 표기에서 ASCII 13자리 token을 찾는다."""
    if not isinstance(value, str):
        return ""
    for token in value.split():
        normalized = token.replace("-", "")
        if len(normalized) == 13 and normalized.isascii() and normalized.isdecimal():
            return normalized
    return ""


def _parse_iso_date(value: object) -> date | None:
    """Kakao ISO datetime에서 날짜 부분만 보존한다."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
