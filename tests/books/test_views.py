from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from books import views as book_views
from books.models import Book
from books.services import BookSearchStatus
from integrations.aladin.contracts import ProviderBook
from integrations.aladin.exceptions import ProviderUnavailableError


class FakeProvider:
    """테스트에서 검색어와 미리 준비한 Provider 응답을 제공한다."""

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
def authenticated_client(client, db):
    user = get_user_model().objects.create_user(
        username="reader",
        password="strong-reader-password-123",
    )
    client.force_login(user)
    return client


@pytest.fixture
def provider_books() -> tuple[ProviderBook, ProviderBook]:
    return (
        ProviderBook(
            isbn13="9788937834790",
            title="같은 제목",
            authors="첫 번째 저자",
            publisher="첫 번째 출판사",
            published_date=date(2014, 11, 20),
            cover_url="https://images.example.test/books/first.jpg",
            description="",
            table_of_contents="",
            external_url="",
        ),
        ProviderBook(
            isbn13="9788937834791",
            title="같은 제목",
            authors="두 번째 저자",
            publisher="두 번째 출판사",
            published_date=date(2020, 12, 1),
            cover_url="",
            description="",
            table_of_contents="",
            external_url="",
        ),
    )


def test_search_requires_authentication(client) -> None:
    response = client.get(reverse("books:search"), {"q": "도서"})

    assert response.status_code == 302
    assert response.url.startswith(f"{reverse('accounts:login')}?next=")


def test_search_shows_initial_screen_for_authenticated_user(
    authenticated_client,
) -> None:
    response = authenticated_client.get(reverse("books:search"))
    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["search_state"] == "initial"
    assert 'for="id_q"' in content
    assert 'href="/books/search/"' in content
    assert 'aria-describedby="search-query-help"' in content
    assert "검색 결과가 없습니다" not in content
    assert "도서를 검색하지 못했습니다" not in content


def test_search_renders_all_provider_books_in_order(
    authenticated_client,
    monkeypatch,
    provider_books: tuple[ProviderBook, ProviderBook],
) -> None:
    provider = FakeProvider(books=provider_books)
    monkeypatch.setattr(book_views, "get_default_provider", lambda: provider)

    response = authenticated_client.get(reverse("books:search"), {"q": "  같은 제목  "})
    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["search_state"] == BookSearchStatus.SUCCESS.value
    assert provider.queries == ["같은 제목"]
    assert content.index("첫 번째 저자") < content.index("두 번째 저자")
    assert "첫 번째 출판사" in content
    assert "2020" in content
    assert 'alt="같은 제목 표지"' in content
    assert "표지 없음" in content


@pytest.mark.parametrize("query", ["", " \t\n ", "가" * 201])
def test_search_rejects_invalid_query_without_creating_provider(
    authenticated_client,
    monkeypatch,
    query: str,
) -> None:
    provider_factory_calls = 0

    def get_provider() -> FakeProvider:
        nonlocal provider_factory_calls
        provider_factory_calls += 1
        return FakeProvider()

    monkeypatch.setattr(book_views, "get_default_provider", get_provider)

    response = authenticated_client.get(reverse("books:search"), {"q": query})

    assert response.status_code == 200
    assert response.context["search_state"] == "input_error"
    assert response.context["form"].errors["q"]
    assert provider_factory_calls == 0
    assert (
        'aria-describedby="search-query-help search-query-error"'
        in response.content.decode()
    )


def test_search_renders_empty_state(authenticated_client, monkeypatch) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(book_views, "get_default_provider", lambda: provider)

    response = authenticated_client.get(reverse("books:search"), {"q": "없는 책"})
    content = response.content.decode()

    assert response.context["search_state"] == BookSearchStatus.EMPTY.value
    assert provider.queries == ["없는 책"]
    assert "검색 결과가 없습니다" in content
    assert "다른 검색어를 입력해 보세요" in content


def test_search_renders_safe_error_with_retry(
    authenticated_client, monkeypatch
) -> None:
    provider = FakeProvider(
        error=ProviderUnavailableError("provider credential detail")
    )
    monkeypatch.setattr(book_views, "get_default_provider", lambda: provider)

    response = authenticated_client.get(reverse("books:search"), {"q": "도서"})
    content = response.content.decode()

    assert response.context["search_state"] == BookSearchStatus.ERROR.value
    assert provider.queries == ["도서"]
    assert "도서를 검색하지 못했습니다" in content
    assert 'form="book-search-form"' in content
    assert "provider credential detail" not in content
    assert "ProviderUnavailableError" not in content


def test_search_does_not_create_books(authenticated_client, monkeypatch) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(book_views, "get_default_provider", lambda: provider)

    response = authenticated_client.get(reverse("books:search"), {"q": "없는 책"})

    assert response.status_code == 200
    assert Book.objects.count() == 0


def test_search_returns_fragment_for_htmx_request(
    authenticated_client, monkeypatch
) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(book_views, "get_default_provider", lambda: provider)

    response = authenticated_client.get(
        reverse("books:search"),
        {"q": "없는 책"},
        HTTP_HX_REQUEST="true",
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert 'id="search-region"' in content
    assert "<!doctype html>" not in content.lower()
    assert 'hx-sync="this:replace"' in content
    assert 'hx-push-url="true"' in content
    assert 'hx-indicator="#search-loading"' in content
    assert 'role="status"' in content
    assert "검색 결과가 없습니다" in content
