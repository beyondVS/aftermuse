import inspect
import json
from datetime import date
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from integrations.aladin import client as aladin_client
from integrations.aladin.client import AladinBookMetadataProvider, get_default_provider
from integrations.aladin.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from integrations.book_metadata.contracts import ProviderBook as CanonicalProviderBook
from integrations.book_metadata.exceptions import (
    ProviderError as CanonicalProviderError,
)


@pytest.fixture
def complete_item() -> dict[str, object]:
    return {
        "isbn13": "9788937834790",
        "title": "정의란 무엇인가",
        "author": "마이클 샌델",
        "publisher": "와이즈베리",
        "pubDate": "2014-11-20",
        "cover": "https://images.example.test/books/justice.jpg",
        "description": "정의에 관한 철학적 질문",
        "link": "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=1",
        "subInfo": {"toc": "1장 옳은 일 하기"},
    }


def _payload(data: object) -> bytes:
    return json.dumps(data).encode()


def test_search_maps_request_and_complete_metadata(
    complete_item: dict[str, object],
) -> None:
    captured: dict[str, object] = {}

    def transport(url: str, timeout: float) -> bytes:
        captured.update(url=url, timeout=timeout)
        return _payload({"item": [complete_item]})

    provider = AladinBookMetadataProvider("test-key", transport=transport, timeout=2.5)

    books = provider.search("정의 와 공정")

    request_query = parse_qs(urlparse(str(captured["url"])).query)
    assert request_query == {
        "ttbkey": ["test-key"],
        "Query": ["정의 와 공정"],
        "QueryType": ["Keyword"],
        "MaxResults": ["20"],
        "start": ["1"],
        "SearchTarget": ["Book"],
        "output": ["js"],
        "Version": ["20131101"],
    }
    assert captured["timeout"] == 2.5
    assert books[0].isbn13 == "9788937834790"
    assert books[0].title == "정의란 무엇인가"
    assert books[0].authors == "마이클 샌델"
    assert books[0].publisher == "와이즈베리"
    assert books[0].published_date == date(2014, 11, 20)
    assert books[0].cover_url == "https://images.example.test/books/justice.jpg"
    assert books[0].description == "정의에 관한 철학적 질문"
    assert books[0].table_of_contents == "1장 옳은 일 하기"
    assert books[0].external_url.endswith("ItemId=1")


def test_search_returns_empty_tuple_for_empty_item_list() -> None:
    provider = AladinBookMetadataProvider(
        "test-key", transport=lambda url, timeout: _payload({"item": []})
    )

    assert provider.search("없는 책") == ()


def test_search_skips_invalid_items_and_preserves_valid_item(
    complete_item: dict[str, object],
) -> None:
    invalid_unicode_isbn = {
        "isbn13": "１２３４５６７８９０１２３",
        "title": "잘못된 ISBN",
    }
    missing_title = {"isbn13": "9788966262281", "title": " "}
    provider = AladinBookMetadataProvider(
        "test-key",
        transport=lambda url, timeout: _payload(
            {"item": [invalid_unicode_isbn, missing_title, complete_item]}
        ),
    )

    books = provider.search("정의")

    assert [book.isbn13 for book in books] == ["9788937834790"]


def test_search_normalizes_missing_optional_metadata() -> None:
    provider = AladinBookMetadataProvider(
        "test-key",
        transport=lambda url, timeout: _payload(
            {
                "item": [
                    {
                        "isbn13": "9788937834790",
                        "title": "정의란 무엇인가",
                        "author": None,
                        "pubDate": "확인되지 않음",
                        "subInfo": "not-an-object",
                    }
                ]
            }
        ),
    )

    book = provider.search("정의")[0]

    assert book.authors == ""
    assert book.publisher == ""
    assert book.published_date is None
    assert book.cover_url == ""
    assert book.description == ""
    assert book.table_of_contents == ""
    assert book.external_url == ""


def test_search_rejects_missing_key_without_transport_call() -> None:
    transport_called = False

    def transport(url: str, timeout: float) -> bytes:
        nonlocal transport_called
        transport_called = True
        return _payload({"item": []})

    provider = AladinBookMetadataProvider(" ", transport=transport)

    with pytest.raises(ProviderConfigurationError) as error:
        provider.search("책")

    assert not transport_called
    assert "test-key" not in str(error.value)


@pytest.mark.parametrize(
    "failure",
    [OSError("network unavailable"), URLError("network unavailable")],
)
def test_search_maps_transport_unavailable_failures(failure: OSError) -> None:
    def transport(url: str, timeout: float) -> bytes:
        raise failure

    provider = AladinBookMetadataProvider("test-key", transport=transport)

    with pytest.raises(ProviderUnavailableError) as error:
        provider.search("책")

    assert "test-key" not in str(error.value)
    assert "network unavailable" not in str(error.value)


def test_search_maps_provider_error_payload_to_unavailable() -> None:
    provider = AladinBookMetadataProvider(
        "test-key",
        transport=lambda url, timeout: _payload(
            {"errorCode": 8, "errorMessage": "key must remain secret"}
        ),
    )

    with pytest.raises(ProviderUnavailableError) as error:
        provider.search("책")

    assert "test-key" not in str(error.value)
    assert "key must remain secret" not in str(error.value)


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        _payload([]),
        _payload({}),
        _payload({"item": {}}),
        _payload({"item": [1]}),
    ],
)
def test_search_rejects_malformed_response(payload: bytes) -> None:
    provider = AladinBookMetadataProvider(
        "test-key", transport=lambda url, timeout: payload
    )

    with pytest.raises(ProviderResponseError):
        provider.search("책")


def test_search_maps_timeouts_separately() -> None:
    def transport(url: str, timeout: float) -> bytes:
        raise TimeoutError

    provider = AladinBookMetadataProvider("test-key", transport=transport)

    with pytest.raises(ProviderTimeoutError):
        provider.search("책")


def test_search_maps_url_error_wrapped_timeout_separately() -> None:
    def transport(url: str, timeout: float) -> bytes:
        raise URLError(TimeoutError())

    provider = AladinBookMetadataProvider("test-key", transport=transport)

    with pytest.raises(ProviderTimeoutError):
        provider.search("책")


def test_get_default_provider_uses_configured_key(settings, monkeypatch) -> None:
    settings.ALADIN_TTB_KEY = "configured-key"
    captured: dict[str, str] = {}

    class FakeProvider:
        def __init__(self, ttb_key: str) -> None:
            captured["ttb_key"] = ttb_key

    monkeypatch.setattr(aladin_client, "AladinBookMetadataProvider", FakeProvider)

    get_default_provider()

    assert captured["ttb_key"] == "configured-key"


def test_adapter_does_not_depend_on_book_model() -> None:
    source = inspect.getsource(aladin_client)

    assert "books.models" not in source
    assert "Book.objects" not in source


def test_legacy_contract_and_exception_imports_reexport_canonical_types() -> None:
    from integrations.aladin.contracts import ProviderBook
    from integrations.aladin.exceptions import ProviderError

    assert ProviderBook is CanonicalProviderBook
    assert ProviderError is CanonicalProviderError
