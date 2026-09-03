import json
from collections.abc import Callable
from datetime import date
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings

from integrations.aladin.contracts import ProviderBook
from integrations.aladin.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

ALADIN_SEARCH_ENDPOINT = "https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
DEFAULT_TIMEOUT_SECONDS = 3.0
Transport = Callable[[str, float], bytes]


def _urlopen_transport(url: str, timeout: float) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return response.read()


class AladinBookMetadataProvider:
    """알라딘 ItemSearch 응답을 Provider 중립 도서 Metadata로 변환한다."""

    def __init__(
        self,
        ttb_key: str,
        *,
        transport: Transport = _urlopen_transport,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._ttb_key = ttb_key.strip()
        self._transport = transport
        self._timeout = timeout

    def search(self, query: str) -> tuple[ProviderBook, ...]:
        """검색어에 해당하는 검증된 도서 Metadata를 반환한다."""
        if not self._ttb_key:
            raise ProviderConfigurationError

        try:
            payload = self._transport(self._build_url(query), self._timeout)
        except TimeoutError as error:
            raise ProviderTimeoutError from error
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise ProviderTimeoutError from error
            raise ProviderUnavailableError from error
        except OSError as error:
            raise ProviderUnavailableError from error

        data = self._decode_payload(payload)
        if "errorCode" in data:
            raise ProviderUnavailableError

        items = data.get("item")
        if not isinstance(items, list):
            raise ProviderResponseError

        return tuple(
            self._parse_item(item) for item in items if self._is_valid_item(item)
        )

    def _build_url(self, query: str) -> str:
        parameters = {
            "ttbkey": self._ttb_key,
            "Query": query,
            "QueryType": "Keyword",
            "MaxResults": "20",
            "start": "1",
            "SearchTarget": "Book",
            "output": "js",
            "Version": "20131101",
        }
        return f"{ALADIN_SEARCH_ENDPOINT}?{urlencode(parameters)}"

    @staticmethod
    def _decode_payload(payload: bytes) -> dict[str, object]:
        """응답을 JSON object로 해석하고 손상된 구조를 Provider 오류로 변환한다."""
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProviderResponseError from error
        if not isinstance(data, dict):
            raise ProviderResponseError
        return data

    @staticmethod
    def _is_valid_item(item: object) -> bool:
        """항목 구조를 검증하고 필수 서지정보의 유효 여부를 반환한다.

        Raises:
            ProviderResponseError: 항목이 JSON object가 아니어서 응답 구조가
                손상된 경우.
        """
        if not isinstance(item, dict):
            raise ProviderResponseError

        isbn13 = _text(item.get("isbn13"))
        title = _text(item.get("title"))
        return (
            len(isbn13) == 13
            and isbn13.isascii()
            and isbn13.isdecimal()
            and bool(title)
        )

    @staticmethod
    def _parse_item(item: object) -> ProviderBook:
        if not isinstance(item, dict):
            raise ProviderResponseError

        sub_info = item.get("subInfo")
        table_of_contents = (
            _text(sub_info.get("toc")) if isinstance(sub_info, dict) else ""
        )
        return ProviderBook(
            isbn13=_text(item.get("isbn13")),
            title=_text(item.get("title")),
            authors=_text(item.get("author")),
            publisher=_text(item.get("publisher")),
            published_date=_parse_date(item.get("pubDate")),
            cover_url=_text(item.get("cover")),
            description=_text(item.get("description")),
            table_of_contents=table_of_contents,
            external_url=_text(item.get("link")),
        )


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def get_default_provider() -> AladinBookMetadataProvider:
    """현재 Django 설정으로 기본 알라딘 Provider를 만든다."""
    return AladinBookMetadataProvider(settings.ALADIN_TTB_KEY)
