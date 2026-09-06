import json
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from integrations.book_metadata.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from integrations.kakao.client import KakaoBookMetadataProvider


def _payload(data: object) -> bytes:
    return json.dumps(data).encode()


def test_search_sends_authorized_kakao_request_and_maps_metadata() -> None:
    captured: dict[str, object] = {}

    def transport(request, timeout: float) -> bytes:
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return _payload(
            {
                "documents": [
                    {
                        "isbn": "9788937834790 8937834796",
                        "title": " 정의란 무엇인가 ",
                        "authors": ["마이클 샌델", "옮긴이"],
                        "publisher": " 와이즈베리 ",
                        "datetime": "2014-11-20T00:00:00.000+09:00",
                        "thumbnail": "https://images.example.test/book.jpg",
                        "contents": "정의에 관한 질문",
                        "url": "https://example.test/book",
                    }
                ]
            }
        )

    books = KakaoBookMetadataProvider("secret-key", transport=transport).search("정의")

    assert parse_qs(urlparse(captured["url"]).query) == {
        "query": ["정의"],
        "sort": ["accuracy"],
        "page": ["1"],
        "size": ["20"],
    }
    assert captured["authorization"] == "KakaoAK secret-key"
    assert captured["timeout"] == 3.0
    assert books[0].isbn13 == "9788937834790"
    assert books[0].authors == "마이클 샌델, 옮긴이"
    assert books[0].published_date == date(2014, 11, 20)
    assert books[0].table_of_contents == ""


def test_search_skips_documents_without_valid_isbn13_or_title() -> None:
    provider = KakaoBookMetadataProvider(
        "key",
        transport=lambda request, timeout: _payload(
            {
                "documents": [
                    {"isbn": "1234567890", "title": "ISBN10만 있음"},
                    {"isbn": "9788937834790", "title": " "},
                    {"isbn": "9788937834791", "title": "유효한 책"},
                ]
            }
        ),
    )

    assert [book.title for book in provider.search("책")] == ["유효한 책"]


@pytest.mark.parametrize(
    "raw_isbn",
    [
        "9788937834790 8937834796",
        "978-89-3783-479-0 8937834796",
        "8937834796 978-89-3783-479-0",
    ],
)
def test_search_normalizes_isbn13_with_spaces_hyphens_and_isbn10(
    raw_isbn: str,
) -> None:
    provider = KakaoBookMetadataProvider(
        "key",
        transport=lambda request, timeout: _payload(
            {"documents": [{"isbn": raw_isbn, "title": "정의란 무엇인가"}]}
        ),
    )

    books = provider.search("정의")

    assert [book.isbn13 for book in books] == ["9788937834790"]


def test_search_returns_empty_tuple_for_empty_documents() -> None:
    provider = KakaoBookMetadataProvider(
        "key", transport=lambda request, timeout: _payload({"documents": []})
    )

    assert provider.search("없는 책") == ()


@pytest.mark.parametrize(
    "failure,error_type",
    [
        (TimeoutError(), ProviderTimeoutError),
        (URLError("network"), ProviderUnavailableError),
        (
            HTTPError("https://example.test", 429, "quota", {}, None),
            ProviderUnavailableError,
        ),
    ],
)
def test_search_maps_transport_failures_without_exposing_diagnostics(
    failure, error_type
) -> None:
    def transport(request, timeout: float) -> bytes:
        raise failure

    with pytest.raises(error_type) as caught:
        KakaoBookMetadataProvider("rest-api-key", transport=transport).search("책")

    assert str(caught.value) == ""
    assert "rest-api-key" not in repr(caught.value)
    if str(failure):
        assert str(failure) not in str(caught.value)


@pytest.mark.parametrize(
    "payload",
    [b"not-json", _payload([]), _payload({}), _payload({"documents": {}})],
)
def test_search_rejects_malformed_top_level_payload_without_exposing_payload(
    payload: bytes,
) -> None:
    provider = KakaoBookMetadataProvider(
        "key", transport=lambda request, timeout: payload
    )

    with pytest.raises(ProviderResponseError) as caught:
        provider.search("책")

    assert str(caught.value) == ""
    assert "key" not in repr(caught.value)
    assert payload.decode(errors="replace") not in str(caught.value)


def test_search_rejects_missing_key_before_transport() -> None:
    called = False

    def transport(request, timeout: float) -> bytes:
        nonlocal called
        called = True
        return _payload({"documents": []})

    with pytest.raises(ProviderConfigurationError):
        KakaoBookMetadataProvider(" ", transport=transport).search("책")

    assert not called
