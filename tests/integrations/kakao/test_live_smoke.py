import os

import pytest

from integrations.kakao.client import KakaoBookMetadataProvider


@pytest.mark.live
def test_kakao_book_search_live_smoke() -> None:
    """실제 key가 있는 환경에서만 Kakao 검색 최소 계약을 확인한다."""
    key = os.environ.get("KAKAO_REST_API_KEY", "")
    if not key:
        pytest.skip("KAKAO_REST_API_KEY가 설정되지 않았습니다.")

    books = KakaoBookMetadataProvider(key).search("정의란 무엇인가")

    assert any(book.isbn13 and book.title for book in books)
